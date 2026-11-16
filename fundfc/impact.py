
import pandas as pd
from sqlalchemy import select

from fundfc.db import Youth, Milestone


DOMAINS = [
    "Housing",
    "Education",
    "Employment",
    "Financial capability",
    "Transportation",
    "Health & wellness",
    "Community & relationships"
]


def impact_summary(session):
    """
    Generate FundFC program-level impact metrics.
    """

    youth = session.scalars(
        select(Youth)
    ).all()

    milestones = session.scalars(
        select(Milestone)
    ).all()

    participants = len(youth)

    active = sum(
        1 for y in youth
        if y.status == "Active"
    )

    milestones_verified = sum(
        1 for m in milestones
        if m.verified
    )

    rows = []

    for domain in DOMAINS:

        domain_milestones = [
            m for m in milestones
            if m.domain == domain
        ]

        completed = sum(
            1 for m in domain_milestones
            if m.status == "Completed"
        )

        verified = sum(
            1 for m in domain_milestones
            if m.verified
        )

        rows.append({
            "Domain": domain,
            "Completed": completed,
            "Verified": verified
        })

    by_domain = pd.DataFrame(rows)

    return {
        "participants": participants,
        "active": active,
        "milestones_verified": milestones_verified,
        "by_domain": by_domain
    }
