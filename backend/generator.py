# ============================================================
# Placement Week Scheduler — Synthetic Data Generator
# Mirai Labs Assignment A
# ============================================================

import random
import numpy as np
from faker import Faker

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

SEED = 42

random.seed(SEED)
np.random.seed(SEED)

fake = Faker()
fake.seed_instance(SEED)

NUM_STUDENTS = 800
NUM_COMPANIES = 35
NUM_ROOMS = 20

# ------------------------------------------------------------
# Branch configuration
# ------------------------------------------------------------

BRANCHES = [
    "CSE",
    "IT",
    "AIML",
    "ECE",
    "EEE",
    "ME",
    "Civil",
]

BRANCH_WEIGHTS = [
    0.27,   # CSE
    0.18,   # IT
    0.15,   # AIML
    0.14,   # ECE
    0.09,   # EEE
    0.10,   # ME
    0.07,   # Civil
]

# ------------------------------------------------------------
# Recognizable company names
#
# These are used only as synthetic entities for demonstration.
# The generated placement data does NOT claim these companies
# actually participated in a placement drive.
# ------------------------------------------------------------

COMPANY_NAMES = [
    "TCS",
    "Infosys",
    "Wipro",
    "Accenture",
    "Cognizant",
    "Capgemini",
    "Deloitte",
    "EY",
    "KPMG",
    "PwC",
    "IBM",
    "Microsoft",
    "Amazon",
    "Google",
    "Oracle",
    "Cisco",
    "SAP",
    "Adobe",
    "NVIDIA",
    "Intel",
    "Dell Technologies",
    "JPMorgan Chase",
    "Goldman Sachs",
    "Morgan Stanley",
    "Wells Fargo",
    "Bosch",
    "Siemens",
    "Qualcomm",
    "PayPal",
    "Zoho",
    "Freshworks",
    "Mphasis",
    "LTIMindtree",
    "Tech Mahindra",
    "HCLTech",
]

# ------------------------------------------------------------
# Company configuration
# ------------------------------------------------------------

TIER_CONFIG = {
    1: {
        "weight": 0.20,
        "cgpa_range": (8.0, 9.0),
        "panels": (1, 3),
        "shortlist": (30, 100),
        "duration": [30, 45, 60],
    },
    2: {
        "weight": 0.35,
        "cgpa_range": (7.0, 8.0),
        "panels": (2, 4),
        "shortlist": (80, 180),
        "duration": [30, 45],
    },
    3: {
        "weight": 0.45,
        "cgpa_range": (5.5, 7.0),
        "panels": (3, 6),
        "shortlist": (150, 350),
        "duration": [15, 20, 30],
    },
}


# ============================================================
# 1. Generate Students
# ============================================================

def generate_students(n=NUM_STUDENTS):
    students = []

    # Generate CGPA distribution.
    # Mean around 7.2 with realistic spread.
    cgpas = np.clip(
        np.random.normal(
            loc=7.2,
            scale=0.9,
            size=n
        ),
        5.0,
        10.0
    )

    for i in range(n):

        branch = random.choices(
            BRANCHES,
            weights=BRANCH_WEIGHTS,
            k=1
        )[0]

        students.append({
            "id": i + 1,
            "name": fake.name(),
            "cgpa": round(float(cgpas[i]), 2),
            "branch": branch,
            "status": "active",
        })

    return students


# ============================================================
# 2. Generate Companies
# ============================================================

def generate_companies(n=NUM_COMPANIES):

    if n > len(COMPANY_NAMES):
        raise ValueError(
            f"Only {len(COMPANY_NAMES)} company names are available."
        )

    companies = []

    # Create a balanced 4-day placement distribution.
    days = []

    for day in range(1, 5):
        days.extend([day] * 8)

    # Remaining 3 companies distributed randomly.
    days.extend([1, 2, 3])

    random.shuffle(days)

    for i in range(n):

        tier = random.choices(
            population=[1, 2, 3],
            weights=[
                TIER_CONFIG[1]["weight"],
                TIER_CONFIG[2]["weight"],
                TIER_CONFIG[3]["weight"],
            ],
            k=1
        )[0]

        config = TIER_CONFIG[tier]

        cgpa_cutoff = round(
            random.uniform(
                config["cgpa_range"][0],
                config["cgpa_range"][1]
            ),
            2
        )

        panel_count = random.randint(
            config["panels"][0],
            config["panels"][1]
        )

        duration = random.choice(
            config["duration"]
        )

        placement_day = days[i]

        # Arrival times vary depending on company.
        arrival_hour = random.choice([
            8,
            8,
            8,
            9
        ])

        arrival_minute = random.choice([
            0,
            15,
            30,
            45
        ])

        arrival_time = (
            f"{arrival_hour:02d}:"
            f"{arrival_minute:02d}:00"
        )

        companies.append({
            "id": i + 1,
            "name": COMPANY_NAMES[i],
            "placement_day": placement_day,
            "arrival_time": arrival_time,
            "cgpa_cutoff": cgpa_cutoff,
            "panels": panel_count,
            "interview_duration_min": duration,
            "priority_tier": tier,
        })

    return companies


# ============================================================
# 3. Weighted Sampling Without Replacement
# ============================================================

def weighted_sample_without_replacement(
    items,
    weights,
    k
):
    """
    Select k unique items using weighted probability.

    Unlike random.choices(), this does NOT select the
    same student multiple times.
    """

    if not items:
        return []

    k = min(k, len(items))

    selected = []

    available_items = list(items)
    available_weights = list(weights)

    for _ in range(k):

        total_weight = sum(available_weights)

        if total_weight <= 0:
            break

        probabilities = [
            weight / total_weight
            for weight in available_weights
        ]

        index = np.random.choice(
            len(available_items),
            p=probabilities
        )

        selected.append(
            available_items[index]
        )

        available_items.pop(index)
        available_weights.pop(index)

    return selected


# ============================================================
# 4. Generate Shortlists
# ============================================================

def generate_shortlists(
    students,
    companies
):

    shortlists = []

    for company in companies:

        # Students meeting CGPA requirement.
        eligible = [
            student
            for student in students
            if student["cgpa"] >= company["cgpa_cutoff"]
        ]

        if not eligible:
            continue

        tier = company["priority_tier"]

        min_size, max_size = TIER_CONFIG[tier]["shortlist"]

        target_size = random.randint(
            min_size,
            max_size
        )

        target_size = min(
            target_size,
            len(eligible)
        )

        # Higher CGPA students have a higher probability
        # of being shortlisted by competitive companies.
        #
        # Small random noise prevents identical probabilities.
        weights = []

        for student in eligible:

            cgpa_factor = student["cgpa"] ** 2

            branch_factor = 1.0

            # Slightly increase probability for technical
            # branches without making other branches impossible.
            if student["branch"] in ["CSE", "IT", "AIML"]:
                branch_factor = 1.15

            noise = random.uniform(
                0.90,
                1.10
            )

            weight = (
                cgpa_factor
                * branch_factor
                * noise
            )

            weights.append(weight)

        selected = weighted_sample_without_replacement(
            eligible,
            weights,
            target_size
        )

        for student in selected:

            shortlists.append({
                "student_id": student["id"],
                "company_id": company["id"],
            })

    return shortlists


# ============================================================
# 5. Generate Rooms
# ============================================================

def generate_rooms(n=NUM_ROOMS):

    rooms = []

    for i in range(n):

        rooms.append({
            "id": i + 1,
            "name": f"Room-{i + 1:02d}",

            # Capacity is kept for future extensibility.
            # Each interview currently occupies one room.
            "capacity": random.choice([
                1,
                1,
                1,
                2
            ]),
        })

    return rooms


# ============================================================
# 6. Generate Panels
# ============================================================

def generate_panels(companies):

    panels = []

    panel_id = 1

    for company in companies:

        for panel_number in range(
            1,
            company["panels"] + 1
        ):

            panels.append({
                "id": panel_id,
                "company_id": company["id"],
                "panel_number": panel_number,
                "status": "available",
            })

            panel_id += 1

    return panels


# ============================================================
# 7. Dataset Summary
# ============================================================

def print_summary(
    students,
    companies,
    shortlists,
    rooms,
    panels
):

    print("\n")
    print("=" * 60)
    print("PLACEMENT SCHEDULER — DATASET SUMMARY")
    print("=" * 60)

    print(f"Students       : {len(students)}")
    print(f"Companies      : {len(companies)}")
    print(f"Rooms          : {len(rooms)}")
    print(f"Panels         : {len(panels)}")
    print(f"Shortlists     : {len(shortlists)}")

    print("\nCompanies by placement day:")

    for day in range(1, 5):

        count = sum(
            1
            for company in companies
            if company["placement_day"] == day
        )

        print(
            f"  Day {day}: {count} companies"
        )

    print("\nCompanies by priority tier:")

    for tier in [1, 2, 3]:

        count = sum(
            1
            for company in companies
            if company["priority_tier"] == tier
        )

        print(
            f"  Tier {tier}: {count} companies"
        )

    print("\nCGPA statistics:")

    cgpas = [
        student["cgpa"]
        for student in students
    ]

    print(
        f"  Minimum : {min(cgpas):.2f}"
    )

    print(
        f"  Maximum : {max(cgpas):.2f}"
    )

    print(
        f"  Average : {np.mean(cgpas):.2f}"
    )

    print("\nTop 10 students by CGPA:")

    top_students = sorted(
        students,
        key=lambda x: x["cgpa"],
        reverse=True
    )[:10]

    for student in top_students:

        shortlist_count = sum(
            1
            for shortlist in shortlists
            if shortlist["student_id"] == student["id"]
        )

        print(
            f"  {student['id']:03d} | "
            f"{student['name']:<25} | "
            f"CGPA {student['cgpa']:.2f} | "
            f"Shortlisted: {shortlist_count}"
        )

    print("=" * 60)


# ============================================================
# 8. Main
# ============================================================

def main():

    print("Generating Placement Scheduler dataset...")

    students = generate_students()

    companies = generate_companies()

    shortlists = generate_shortlists(
        students,
        companies
    )

    rooms = generate_rooms()

    panels = generate_panels(
        companies
    )

    print_summary(
        students,
        companies,
        shortlists,
        rooms,
        panels
    )

    return {
        "students": students,
        "companies": companies,
        "shortlists": shortlists,
        "rooms": rooms,
        "panels": panels,
    }


if __name__ == "__main__":
    dataset = main()