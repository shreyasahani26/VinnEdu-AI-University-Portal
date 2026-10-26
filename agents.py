
# ============================================================
# VinnEdu AI - AI Agent Routing
# ============================================================

AGENTS = [
    (
        "Admission Agent",
        "Handles admission-related questions, eligibility, "
        "application procedures and admission requirements."
    ),
    (
        "Attendance Agent",
        "Handles attendance records, attendance percentages "
        "and attendance-related questions."
    ),
    (
        "Timetable Agent",
        "Handles class schedules, lecture timings, subjects "
        "and timetable questions."
    ),
    (
        "Academic Agent",
        "Handles subjects, examinations, assignments, "
        "results and academic queries."
    ),
    (
        "Management Agent",
        "Handles general university administration questions."
    ),
    (
        "IT/Helpdesk Agent",
        "Handles technical problems, login issues and "
        "university portal support."
    ),
    (
        "Library Agent",
        "Handles library access, borrowing, returns and study resources."
    ),
    (
        "Finance Agent",
        "Handles tuition fees, payments, receipts and account balances."
    ),
    (
        "Scholarship Agent",
        "Handles scholarship eligibility, applications and deadlines."
    ),
    (
        "Transport Agent",
        "Handles campus transport routes, passes and schedules."
    ),
    (
        "Hostel Agent",
        "Handles accommodation, residence rules and hostel requests."
    ),
]


ROUTING_RULES = [
    {
        "name": "Attendance Agent",
        "keywords": [
            "attendance",
            "present",
            "absent",
            "attended",
            "attendance percentage",
            "attendance record",
        ],
        "response": (
            "Your question has been routed to the Attendance Agent. "
            "This demo currently performs keyword-based routing. "
            "Actual attendance details require a connected attendance database."
        ),
    },
    {
        "name": "Timetable Agent",
        "keywords": [
            "timetable",
            "schedule",
            "class",
            "lecture",
            "class timing",
            "next class",
            "subject timing",
        ],
        "response": (
            "Your question has been routed to the Timetable Agent. "
            "This demo identifies timetable-related questions. "
            "Live timetable answers require timetable database integration."
        ),
    },
    {
        "name": "Admission Agent",
        "keywords": [
            "admission",
            "eligibility",
            "application",
            "enrollment",
            "enrolment",
            "admission form",
            "admission process",
        ],
        "response": (
            "Your question has been routed to the Admission Agent. "
            "For verified admission information, connect the agent "
            "to your university's official admission data."
        ),
    },
    {
        "name": "Academic Agent",
        "keywords": [
            "exam",
            "examination",
            "result",
            "marks",
            "assignment",
            "subject",
            "semester",
            "grade",
            "syllabus",
        ],
        "response": (
            "Your question has been routed to the Academic Agent. "
            "Verified results and academic records require integration "
            "with the appropriate university database."
        ),
    },
    {
        "name": "IT/Helpdesk Agent",
        "keywords": [
            "login",
            "password",
            "technical",
            "error",
            "portal",
            "website",
            "bug",
            "account",
            "reset password",
        ],
        "response": (
            "Your question has been routed to the IT/Helpdesk Agent. "
            "Please provide the relevant technical details if you "
            "need help troubleshooting a portal issue."
        ),
    },
    {
        "name": "Library Agent",
        "keywords": ["library", "book", "borrow", "return", "catalog"],
        "response": (
            "Your question has been routed to the Library Agent. "
            "Current library availability requires a connected library system."
        ),
    },
    {
        "name": "Finance Agent",
        "keywords": ["fee", "tuition", "payment", "receipt", "balance"],
        "response": (
            "Your question has been routed to the Finance Agent. "
            "Account-specific information requires a connected finance system."
        ),
    },
    {
        "name": "Scholarship Agent",
        "keywords": ["scholarship", "financial aid", "grant", "stipend"],
        "response": (
            "Your question has been routed to the Scholarship Agent. "
            "Verify application details with the university scholarship office."
        ),
    },
    {
        "name": "Transport Agent",
        "keywords": ["bus", "transport", "shuttle", "route", "bus pass"],
        "response": (
            "Your question has been routed to the Transport Agent. "
            "Live route and timing information requires a connected transport system."
        ),
    },
    {
        "name": "Hostel Agent",
        "keywords": ["hostel", "dorm", "residence", "accommodation", "room allotment"],
        "response": (
            "Your question has been routed to the Hostel Agent. "
            "Room availability requires a connected residence system."
        ),
    },
]


def answer_query(query):
    """
    Route a user query using keyword matching.

    Returns:
        agent_name: str
        match_score: float between 0 and 1
        response: str
        matched_keywords: list[str]

    The score is a keyword-matching score, not model accuracy
    or a calibrated AI confidence probability.
    """

    if not isinstance(query, str) or not query.strip():
        return (
            "Management Agent",
            0.0,
            "Please enter a question so the appropriate agent can be selected.",
            [],
        )

    normalized_query = " ".join(query.lower().split())

    best_agent = "Management Agent"
    best_score = 0.0
    best_response = (
        "Your question has been routed to the Management Agent. "
        "This demo uses keyword-based routing. Connect a verified "
        "university knowledge base to provide specific answers."
    )
    best_matches = []

    for rule in ROUTING_RULES:
        matches = [
            keyword
            for keyword in rule["keywords"]
            if keyword in normalized_query
        ]

        # Score = proportion of this rule's keywords that matched.
        score = len(matches) / len(rule["keywords"])

        if score > best_score:
            best_score = score
            best_agent = rule["name"]
            best_response = rule["response"]
            best_matches = matches

    return (
        best_agent,
        round(best_score, 4),
        best_response,
        best_matches,
    )
