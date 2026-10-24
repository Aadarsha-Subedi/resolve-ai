# Dashboard API

`GET /api/workspaces/{workspace_id}/dashboard/` returns everything the dashboard screen shows in one call (implemented in the `audit` app). Session cookie auth. Owner and member (`dashboard.view`); non-members and removed members get 404. Read-only.

## Query parameters

All optional. Unknown or blank parameters return 400.

| Name | Values | Default |
| --- | --- | --- |
| `period` | `7d`, `30d`, `90d` (the last N local days ending today) | `30d` |
| `from`, `to` | `YYYY-MM-DD`, inclusive, at most 366 days; both required together; not combined with `period` | none |
| `tz` | IANA name, for example `Asia/Kathmandu` | `UTC` |
| `include` | comma list of `summary`, `volume`, `recent_tickets`, `waiting`, `activity` | all |
| `recent_limit`, `waiting_limit`, `activity_limit` | 1 to 50 | 5, 5, 10 |

## Response

The standard envelope. `data` is below. `meta.cached` is `true` when the 30-second cache answered. Sections not named in `include` are absent from `data`.

```ts
type DashboardResponse = {
  success: true;
  status_code: 200;
  message: string;
  data: Dashboard;
  meta: { cached: boolean };
};

type Dashboard = {
  generated_at: string; // ISO 8601 UTC; when the (possibly cached) data was computed
  period: {
    key: "7d" | "30d" | "90d" | "custom";
    from: string; // YYYY-MM-DD, local day, inclusive
    to: string;   // YYYY-MM-DD, local day, inclusive
    days: number;
    tz: string;
    previous: { from: string; to: string }; // same length, right before `from`
  };
  summary?: {
    active: number; // open + in_progress + pending
    by_status: { open: number; in_progress: number; pending: number };
    urgent: number;            // active and priority urgent
    high: number;              // active and priority high (separate from urgent)
    waiting_for_reply: number; // active, last customer message later than last agent reply
    created: { current: number; previous: number };
    resolved: { current: number; previous: number }; // by resolved_at
  };
  volume?: {
    granularity: "day" | "week"; // day up to 31 days, otherwise 7-day buckets from `period.from`
    buckets: {
      start: string;   // YYYY-MM-DD
      end: string;     // YYYY-MM-DD inclusive (the last week bucket may be shorter)
      created: number;
      resolved: number;
    }[]; // zero-filled, oldest first, no gaps
  };
  recent_tickets?: {
    items: {
      id: string; // uuid
      number: number;
      subject: string;
      customer_name: string; // may be ""
      status: "open" | "in_progress" | "pending" | "resolved" | "closed";
      priority: "low" | "medium" | "high" | "urgent";
      category: "billing" | "technical" | "account" | "feature_request" | "general" | "other";
      waiting_for_reply: boolean;
      created_at: string;       // ISO 8601 UTC
      last_activity_at: string; // ISO 8601 UTC; newest first
    }[];
  };
  waiting?: {
    total: number; // all waiting tickets, not just the ones returned
    items: {
      id: string;
      number: number;
      subject: string;
      customer_name: string;
      status: "open" | "in_progress" | "pending";
      priority: "low" | "medium" | "high" | "urgent";
      waiting_since: string; // ISO 8601 UTC; longest-waiting first
    }[];
  };
  activity?: {
    items: {
      id: string;
      source: "ticket";
      event_type:
        | "created" | "status_changed" | "priority_changed" | "category_changed"
        | "details_changed" | "public_reply_added" | "internal_note_added"
        | "customer_reply_received" | "email_delivery_failed";
      ticket: { id: string; number: number; subject: string };
      actor: { id: string; name: string } | null; // null for customers and the system
      old_value: string | null; // only for status/priority/category changes
      new_value: string | null; // only for status/priority/category changes
      created_at: string; // ISO 8601 UTC; newest first
    }[];
  };
};
```

Message text, internal notes and customer email addresses are never included.

## Errors

Same envelope with `success: false`: 400 for invalid parameters, 401 not signed in, 404 not a member (or unknown workspace), 429 over 30 requests a minute.
