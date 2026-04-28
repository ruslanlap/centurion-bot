WELCOME_BOT = (
    "Hello! I'm your task manager bot.\n"
    "I can help you create and track tasks in this group.\n\n"
    "Use /help to see available commands."
)

HELP = (
    "<b>Available commands:</b>\n\n"
    "<b>Tasks:</b>\n"
    "/do &lt;title&gt; — Create a task\n"
    "/do &lt;title&gt; @user in N days — Assign in group\n"
    "/tasks — Show tasks\n"
    "/stats — Show statistics\n"
    "/due — Tasks due today\n"
    "/weekly — Weekly review\n\n"
    "<b>Priorities:</b> add <code>!high</code> or "
    "<code>!low</code> to /do\n\n"
    "<b>Recurring tasks:</b>\n"
    "/repeat &lt;title&gt; daily|weekly|monthly\n"
    "/repeats — List active recurring tasks\n\n"
    "<b>Check-ins:</b>\n"
    "/checkin — Submit daily report\n"
    "/checkin_report — View today's reports\n\n"
    "<b>Other:</b>\n"
    "/feedback &lt;text&gt; — Send feedback\n"
    "/help — Show this message\n\n"
    "<b>Admin:</b>\n"
    "/admin_stats — Bot statistics\n"
    "/admin_announce &lt;text&gt; — Announcement\n"
    "/admin_feedback_show — Feedback list\n"
    "/admin_feedback_reply &lt;id&gt; &lt;text&gt;\n"
    "/admin_feedback_close &lt;id&gt;"
)

ADD_TO_GROUP = "Please add the bot to a group to get started!"

MISSING_TITLE = "Please include a task title, {name}!"
SELECT_CHAT = "Which group should this task go to?\nSelect below!"
SELECT_USER = "Who should work on <b>{title}</b>?\nSelect below!"
SELECT_DATE = "Select a due date!"

ADDED_TASK = "Task <b>{title}</b> assigned to {user_name}."
ADDED_TASK_GROUP = "{owner_name} assigned <b>{title}</b> to {user_name}{due_text}."

UPDATE_DUE_REQUEST = "{user_name} requested to change the due date of <b>{title}</b> from {prev_due} to {new_due}."
UPDATE_DUE_ACCEPTED = (
    "{requestee} accepted {requestor}'s request to change the due date of <b>{title}</b> "
    "from {prev_due} to {new_due}."
)
UPDATE_DUE_DENIED = (
    "{requestee} denied {requestor} to update the due date of <b>{title}</b> "
    "from {prev_due} to {new_due}."
)
UPDATE_DENIED = "You denied the request."
UPDATE_GRANTED = "You accepted the request."
DUE_UPDATED = "The due date has been updated."
UPDATED_TASK_REQUESTED = "Requested {user_name} to update your task."

BTN_COMPLETE = "Complete"
BTN_EDIT_DATE = "Edit date"
BTN_SHOW_TASK = "Show details"
BTN_ACCEPT = "Accept"
BTN_DENY = "Deny"

SUMMARY_HEADLINE = "Your open tasks"
SUMMARY_OVERDUE = "Overdue"
SUMMARY_DUE_TODAY = "Due today"
SUMMARY_DUE_THIS_WEEK = "This week"
SUMMARY_DUE_LATER = "Later"
SUMMARY_DUE_UNDEFINED = "No due date"

NO_TASKS = "Nothing to do right now, enjoy!"
TASK_DONE = "Task <b>{title}</b> completed!"
TASK_DONE_GROUP = "{owner_name}: {user_name} completed <b>{title}</b>!"

TASK_HEADLINE_ASSIGNED = "Tasks you have been assigned"
TASK_HEADLINE_OWNING = "Your tasks for others"
TASK_HEADLINE_GROUP = "Tasks for anyone in the group"
TASK_OVERVIEW_PRIVATE = "Switch to the private chat to view all of your assigned tasks!"

REVIEW_HEADLINE = "Weekly review for <b>{chat_title}</b>"
REVIEW_SUMMARY = (
    "{created} task(s) created and {done} task(s) completed"
    "{on_time_text}."
)
REVIEW_COMPARISON = (
    "Compared to the previous week: created tasks {created_dir} by {created_diff}, "
    "completed tasks {done_dir} by {done_diff}."
)
REVIEW_DONE_TASKS = "Tasks completed this week:"
REVIEW_INCOMPLETE = "Still open:"
REVIEW_UPCOMING = "Due this week:"
REVIEW_MOTIVATION = "Keep up the great work!"
RANKING = "User ranking"

STATS_DONE = "{count} task(s) completed, {on_time} on time, {late} late."
STATS_OPEN = "{count} task(s) open, {on_time} in time, {late} overdue."

DO_GROUP_FORMAT = (
    "Please use the format:\n"
    "<code>/do [title] @[username] in [count] [days|weeks|...]</code>\n"
    "e.g. <code>/do cleanup @sam in 3 days</code>\n"
    "e.g. <code>/do cleanup in 2 weeks</code>"
)
USER_NOT_REGISTERED = "@{user_name}: please send a message in the chat so the bot can register you!"

USER_WELCOME = "Welcome to <b>{chat_title}</b>, {name}! You are now registered."
USER_GOODBYE = "Goodbye, {name}!"

ANNOUNCEMENT_PREFIX = "Announcement:"
ANNOUNCEMENT_SENT = "Announcement sent to {success} user(s), {failed} failed."
FEEDBACK_THANKS = "Thanks for your feedback!"
FEEDBACK_NEW = "New feedback received!"
FEEDBACK_NONE = "No unresolved feedback."
FEEDBACK_NOT_FOUND = "Feedback not found."
FEEDBACK_CLOSED = "Feedback marked as resolved."
FEEDBACK_REPLY_PREFIX = "Reply from admin:"
FEEDBACK_REPLY_POSTFIX = "Use /feedback <text> to respond."
FEEDBACK_INCLUDE_ID = "Please include the feedback ID."
MISSING_TEXT = "Please include some text, {name}!"

AUTO_REGISTERED = "Auto-registered {count} member(s) from this group."

# ---- Recurring tasks ----

REPEAT_USAGE = (
    "<b>Create a recurring task:</b>\n"
    "<code>/repeat [title] [daily|weekly|monthly]</code>\n\n"
    "Options: add <code>!high</code> or <code>!low</code> for priority.\n\n"
    "Examples:\n"
    "<code>/repeat Clean lobby daily</code>\n"
    "<code>/repeat Inventory check weekly !high</code>\n"
    "<code>/repeat Monthly report monthly</code>"
)

REPEAT_CREATED = (
    "Recurring task created!\n"
    "Title: <b>{title}</b>\n"
    "Schedule: {schedule}\n"
    "Priority: {priority}\n"
    "ID: #{id}"
)

NO_RECURRING = "No active recurring tasks."
RECURRING_LIST_HEADER = "Active recurring tasks"
REPEAT_STOPPED = "Recurring task #{id} has been stopped."

RECURRING_GENERATED = "Recurring task generated: <b>{title}</b> (due {due})."

# ---- Priorities ----

PRIORITY_SET = "Priority set to {priority} for task <b>{title}</b>."

# ---- Escalation ----

ESCALATION_ALERT = (
    "🔴 <b>Escalation:</b> High-priority task <b>{title}</b> is overdue!\n"
    "Assigned to {user_name}, created by {owner_name}.\n"
    "Due: {due}"
)

# ---- Check-ins ----

CHECKIN_USAGE = (
    "<b>Submit a check-in:</b>\n"
    "<code>/checkin\n"
    "done: what you completed\n"
    "plan: what you will do next\n"
    "blockers: what blocks you</code>\n\n"
    "Or simply: <code>/checkin finished the report</code>"
)

CHECKIN_SAVED = "Check-in saved, {name}!{streak}"

CHECKIN_BLOCKER_ALERT = (
    "⚠️ <b>Blocker reported by {name}:</b>\n{blockers}"
)

CHECKIN_REPORT_HEADER = "Today's check-ins"
CHECKIN_MISSING = "Haven't checked in yet"

CHECKIN_REMINDER = "Don't forget to check in today! Use /checkin to report your status."
