from typing import List, Optional

from dispatch.individual import service as individual_service
from dispatch.individual.models import IndividualContact
from dispatch.participant_role import service as participant_role_service
from dispatch.participant_role.models import ParticipantRole, ParticipantRoleCreate
from dispatch.plugin import service as plugin_service
from dispatch.service import service as service_service

from .models import Participant, ParticipantCreate, ParticipantUpdate


def get(*, db_session, participant_id: int) -> Optional[Participant]:
    """Get a participant by its id."""
    return db_session.query(Participant).filter(Participant.id == participant_id).first()


def get_by_incident_id_and_role(
    *, db_session, incident_id: int, role: str
) -> Optional[Participant]:
    """Get a participant by incident id and role name."""
    return (
        db_session.query(Participant)
        .join(ParticipantRole)
        .filter(Participant.incident_id == incident_id)
        .filter(ParticipantRole.renounced_at.is_(None))
        .filter(ParticipantRole.role == role)
        .one_or_none()
    )


def get_by_incident_id_and_email(
    *, db_session, incident_id: int, email: str
) -> Optional[Participant]:
    """Get a participant by incident id and email."""
    return (
        db_session.query(Participant)
        .join(IndividualContact)
        .filter(Participant.incident_id == incident_id)
        .filter(IndividualContact.email == email)
        .one_or_none()
    )


def get_by_incident_id_and_service_id(
    *, db_session, incident_id: int, service_id: int
) -> Optional[Participant]:
    """Get participant by incident and service id."""
    return (
        db_session.query(Participant)
        .filter(Participant.incident_id == incident_id)
        .filter(Participant.service_id == service_id)
        .one_or_none()
    )


def get_by_incident_id_and_conversation_id(
    *, db_session, incident_id: int, user_conversation_id: str
) -> Optional[Participant]:
    """Get participant by incident and user_conversation id."""
    return (
        db_session.query(Participant)
        .filter(Participant.incident_id == incident_id)
        .filter(Participant.user_conversation_id == user_conversation_id)
        .one_or_none()
    )


def get_all(*, db_session) -> List[Optional[Participant]]:
    """Get all participants."""
    return db_session.query(Participant)


def get_all_by_incident_id(*, db_session, incident_id: int) -> List[Optional[Participant]]:
    """Get all participants by incident id."""
    return db_session.query(Participant).filter(Participant.incident_id == incident_id)


def get_or_create(
    *,
    db_session,
    incident_id: int,
    individual_id: int,
    service_id: int,
    participant_roles: List[ParticipantRoleCreate],
) -> Participant:
    """Gets an existing participant object or creates a new one."""
    from dispatch.incident import service as incident_service

    participant = (
        db_session.query(Participant)
        .filter(Participant.incident_id == incident_id)
        .filter(Participant.individual_contact_id == individual_id)
        .one_or_none()
    )

    if not participant:
        incident = incident_service.get(db_session=db_session, incident_id=incident_id)

        # We get information about the individual
        individual_contact = individual_service.get(
            db_session=db_session, individual_contact_id=individual_id
        )

        individual_info = {}
        contact_plugin = plugin_service.get_active_instance(
            db_session=db_session, project_id=incident.project.id, plugin_type="contact"
        )
        if contact_plugin:
            individual_info = contact_plugin.instance.get(
                individual_contact.email, db_session=db_session
            )

        location = individual_info.get("location", "Unknown")
        team = individual_info.get("team", "Unknown")
        department = individual_info.get("department", "Unknown")

        participant_in = ParticipantCreate(
            participant_roles=participant_roles,
            team=team,
            department=department,
            location=location,
        )

        if service_id:
            participant_in.service = {"id": service_id}

        participant = create(db_session=db_session, participant_in=participant_in)
    else:
        # we add additional roles to the participant
        for participant_role in participant_roles:
            participant.participant_roles.append(
                participant_role_service.create(
                    db_session=db_session, participant_role_in=participant_role
                )
            )

        if not participant.service:
            # we only associate the service with the participant once to prevent overwrites
            service = service_service.get(db_session=db_session, service_id=service_id)
            if service:
                participant.service_id = service_id
                participant.service = service

        db_session.commit()

    return participant


def create(*, db_session, participant_in: ParticipantCreate) -> Participant:
    """Create a new participant."""
    participant_roles = [
        participant_role_service.create(db_session=db_session, participant_role_in=participant_role)
        for participant_role in participant_in.participant_roles
    ]

    service = None
    if participant_in.service:
        service = service_service.get(db_session=db_session, service_id=participant_in.service.id)

    participant = Participant(
        **participant_in.dict(exclude={"participant_roles", "service"}),
        service=service,
        participant_roles=participant_roles,
    )

    db_session.add(participant)
    db_session.commit()
    return participant


def create_all(*, db_session, participants_in: List[ParticipantCreate]) -> List[Participant]:
    """Create a list of participants."""
    participants = [Participant(**t.dict()) for t in participants_in]
    db_session.bulk_save_objects(participants)
    db_session.commit()
    return participants


def update(
    *, db_session, participant: Participant, participant_in: ParticipantUpdate
) -> Participant:
    """Updates a participant."""
    participant_data = participant.dict()

    update_data = participant_in.dict(skip_defaults=True)

    for field in participant_data:
        if field in update_data:
            setattr(participant, field, update_data[field])

    db_session.commit()
    return participant


def delete(*, db_session, participant_id: int):
    """Deletes a participant."""
    participant = db_session.query(Participant).filter(Participant.id == participant_id).first()
    db_session.delete(participant)
    db_session.commit()
