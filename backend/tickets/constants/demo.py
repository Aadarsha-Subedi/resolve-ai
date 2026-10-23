"""Sample tickets for the demo workspace (written by us; every person and address is fictional).

Each thread entry is (hours before now, kind, body). The first entry is always the
customer's opening message, which becomes the ticket description. Kinds: "customer"
(inbound public), "reply" (agent public reply), "note" (internal note).
"""

CUSTOMER = "customer"
REPLY = "reply"
NOTE = "note"

DEMO_TICKETS: list[dict] = [
    {
        "subject": "Charged twice for the March renewal",
        "customer_name": "Maya Okafor",
        "customer_email": "maya.okafor@example.com",
        "category": "billing",
        "priority": "urgent",
        "status": "open",
        "source": "email",
        "assigned": False,
        "thread": [
            (
                0.6,
                CUSTOMER,
                "Hi, my card statement shows two charges of $49 for our studio plan on "
                "March 3. We only have one studio. Can you refund the duplicate?\n\n"
                "Maya, Lotus Room Yoga",
            ),
        ],
    },
    {
        "subject": "Class reminders stopped reaching members",
        "customer_name": "Lucas Brennan",
        "customer_email": "lucas@example.org",
        "category": "technical",
        "priority": "high",
        "status": "in_progress",
        "source": "portal",
        "assigned": True,
        "thread": [
            (
                27,
                CUSTOMER,
                "Since Monday none of our members get the 2-hour reminder email before "
                "class. Nothing changed on our side.",
            ),
            (
                26,
                NOTE,
                "Reminder job logs show bounces from their custom sender domain. "
                "Probably an SPF record issue after their DNS move.",
            ),
            (
                25.5,
                REPLY,
                "Thanks Lucas. It looks like the sender domain lost its SPF record when "
                "your DNS moved. Could you add the record from Settings > Email > Sender "
                "domain and tell me when it is in place?",
            ),
            (
                3,
                CUSTOMER,
                "Added it this morning. Still no reminders for the 6pm class.",
            ),
        ],
    },
    {
        "subject": "Crash when booking from the iPhone app",
        "customer_name": "Priya Raman",
        "customer_email": "priya.raman@example.net",
        "category": "technical",
        "priority": "urgent",
        "status": "in_progress",
        "source": "email",
        "assigned": True,
        "thread": [
            (
                7,
                CUSTOMER,
                "Members say the app closes as soon as they tap Book on any Saturday "
                "class. Android seems fine.",
            ),
            (
                6.5,
                NOTE,
                "Reproduced on iOS 18.2 with a class that has a waitlist. Escalated to "
                "the mobile team.",
            ),
            (
                6,
                REPLY,
                "Thanks Priya, we can reproduce it and the mobile team is on it. Until "
                "the fix ships, members can book from the website without any issue.",
            ),
        ],
    },
    {
        "subject": "Google Calendar shows classes an hour late",
        "customer_name": "Tomás Ibarra",
        "customer_email": "tomas@example.com",
        "category": "technical",
        "priority": "high",
        "status": "open",
        "source": "portal",
        "assigned": False,
        "thread": [
            (
                5,
                CUSTOMER,
                "Our instructors' synced calendars show every class one hour after the "
                "real start time. The studio is in Lisbon.",
            ),
        ],
    },
    {
        "subject": "Adding a second instructor login",
        "customer_name": "Hannah Li",
        "customer_email": "hannah.li@example.org",
        "category": "account",
        "priority": "medium",
        "status": "pending",
        "source": "portal",
        "assigned": True,
        "thread": [
            (
                74,
                CUSTOMER,
                "How do I give our new instructor her own login? I don't want to share "
                "mine.",
            ),
            (
                71,
                REPLY,
                "Happy to help, Hannah. Extra logins are included from the Studio plan. "
                "Which plan are you on? I can switch it for you and send the invite.",
            ),
        ],
    },
    {
        "subject": "Invoice needs our VAT number",
        "customer_name": "Jonas Weber",
        "customer_email": "jonas.weber@example.com",
        "category": "billing",
        "priority": "medium",
        "status": "pending",
        "source": "email",
        "assigned": True,
        "thread": [
            (
                30,
                CUSTOMER,
                "Our accountant needs the VAT number on last month's invoice. Can you "
                "reissue it?",
            ),
            (
                22,
                REPLY,
                "Of course. Please reply with the VAT number exactly as it should "
                "appear and I will reissue the invoice the same day.",
            ),
        ],
    },
    {
        "subject": "Change the studio address on the booking page",
        "customer_name": "Amara Diallo",
        "customer_email": "amara@example.net",
        "category": "account",
        "priority": "low",
        "status": "open",
        "source": "email",
        "assigned": False,
        "thread": [
            (
                20,
                CUSTOMER,
                "We moved to Unit 4, 18 Harbour Street. The booking page still shows the "
                "old address and I can't find where to edit it.",
            ),
        ],
    },
    {
        "subject": "Waitlist for full classes",
        "customer_name": "Sofia Marchetti",
        "customer_email": "sofia@example.org",
        "category": "feature_request",
        "priority": "low",
        "status": "open",
        "source": "portal",
        "assigned": True,
        "thread": [
            (
                52,
                CUSTOMER,
                "Could members join a waitlist when a class is full and get the spot "
                "automatically if someone cancels?",
            ),
            (
                30,
                NOTE,
                "Third studio asking this month. Added to the roadmap request.",
            ),
            (
                29,
                REPLY,
                "Great idea, Sofia. It is on our roadmap and I have added your studio "
                "to the request so you hear first when it ships.",
            ),
        ],
    },
    {
        "subject": "Refund for the cancelled annual plan",
        "customer_name": "Kenji Sato",
        "customer_email": "kenji.sato@example.com",
        "category": "billing",
        "priority": "high",
        "status": "resolved",
        "source": "email",
        "assigned": True,
        "thread": [
            (
                150,
                CUSTOMER,
                "We closed the second location and cancelled its annual plan. Can we "
                "get the unused months back?",
            ),
            (
                147,
                REPLY,
                "Sorry to hear about the location, Kenji. I have refunded the 7 unused "
                "months to the original card; it shows within 5 to 10 days.",
            ),
            (126, CUSTOMER, "Received, thank you!"),
        ],
    },
    {
        "subject": "Locked out after changing my email",
        "customer_name": "Nora Kowalski",
        "customer_email": "nora.k@example.net",
        "category": "account",
        "priority": "urgent",
        "status": "resolved",
        "source": "portal",
        "assigned": True,
        "thread": [
            (
                220,
                CUSTOMER,
                "I changed my login email yesterday and now the sign-in link never "
                "arrives. Classes start in an hour.",
            ),
            (
                219.5,
                NOTE,
                "Old address was still on the account as primary. Swapped it.",
            ),
            (
                219.4,
                REPLY,
                "Fixed, Nora. Your new address is now the primary one; a sign-in link "
                "is on its way.",
            ),
        ],
    },
    {
        "subject": "Payment page in Spanish",
        "customer_name": "Elena Petrova",
        "customer_email": "elena@example.com",
        "category": "feature_request",
        "priority": "low",
        "status": "resolved",
        "source": "email",
        "assigned": True,
        "thread": [
            (
                290,
                CUSTOMER,
                "Many of our members speak Spanish. Can the payment page be shown in "
                "Spanish?",
            ),
            (
                286,
                REPLY,
                "Yes. Turn on Spanish under Settings > Booking page > Languages and the "
                "payment page follows the member's browser language.",
            ),
        ],
    },
    {
        "subject": "Export the member list to CSV",
        "customer_name": "Rita Gomes",
        "customer_email": "rita.gomes@example.org",
        "category": "general",
        "priority": "medium",
        "status": "closed",
        "source": "portal",
        "assigned": True,
        "thread": [
            (
                360,
                CUSTOMER,
                "Is there a way to export all members with their class pack balance?",
            ),
            (
                356,
                REPLY,
                "There is: Members > Export > CSV includes the balance column. Let me "
                "know if anything looks off.",
            ),
            (330, CUSTOMER, "Found it, works perfectly."),
        ],
    },
    {
        "subject": "Question about class pack expiry",
        "customer_name": "Ade Mensah",
        "customer_email": "ade@example.com",
        "category": "general",
        "priority": "low",
        "status": "closed",
        "source": "email",
        "assigned": False,
        "thread": [
            (
                460,
                CUSTOMER,
                "Do unused class packs expire? A member is asking before buying a "
                "20-pack.",
            ),
            (
                452,
                REPLY,
                "Packs expire after the period you set on each pack (12 months by "
                "default). You can change it under Pricing > Class packs.",
            ),
        ],
    },
]
