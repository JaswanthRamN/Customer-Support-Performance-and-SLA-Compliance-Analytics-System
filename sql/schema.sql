-- Fictional customer-support portfolio dataset. Run with a role allowed to
-- create a schema and tables. Re-running this file leaves existing rows intact.
CREATE SCHEMA IF NOT EXISTS support_analytics;

CREATE TABLE IF NOT EXISTS support_analytics.sla_policies (
    priority TEXT PRIMARY KEY CHECK (priority IN ('Critical', 'High', 'Medium', 'Low')),
    response_target_minutes INTEGER NOT NULL CHECK (response_target_minutes > 0),
    resolution_target_minutes INTEGER NOT NULL CHECK (resolution_target_minutes > 0),
    assumption_note TEXT NOT NULL,
    CONSTRAINT sla_policy_values_unique
        UNIQUE (priority, response_target_minutes, resolution_target_minutes)
);

INSERT INTO support_analytics.sla_policies
    (priority, response_target_minutes, resolution_target_minutes, assumption_note)
VALUES
    ('Critical', 15, 240, 'Illustrative project assumption; elapsed calendar time'),
    ('High', 60, 480, 'Illustrative project assumption; elapsed calendar time'),
    ('Medium', 240, 1440, 'Illustrative project assumption; elapsed calendar time'),
    ('Low', 480, 4320, 'Illustrative project assumption; elapsed calendar time')
ON CONFLICT (priority) DO UPDATE SET
    response_target_minutes = EXCLUDED.response_target_minutes,
    resolution_target_minutes = EXCLUDED.resolution_target_minutes,
    assumption_note = EXCLUDED.assumption_note;

CREATE TABLE IF NOT EXISTS support_analytics.customers (
    customer_id TEXT PRIMARY KEY CHECK (customer_id ~ '^CU[0-9]+$'),
    customer_label TEXT NOT NULL CHECK (customer_label ~ '^Synthetic Customer [0-9]+$'),
    segment TEXT NOT NULL CHECK (segment IN ('Individual', 'Small Business', 'Enterprise')),
    region TEXT NOT NULL CHECK (region IN ('Region A', 'Region B', 'Region C', 'Region D')),
    joined_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS support_analytics.teams (
    team_id TEXT PRIMARY KEY CHECK (team_id ~ '^TM[0-9]+$'),
    team_name TEXT NOT NULL UNIQUE CHECK (team_name IN ('Tier 1 Support', 'Technical Support', 'Billing Support')),
    specialization TEXT NOT NULL CHECK (specialization IN ('Account and General', 'Technical', 'Billing')),
    CONSTRAINT team_specialization_match CHECK (
        (team_name = 'Tier 1 Support' AND specialization = 'Account and General') OR
        (team_name = 'Technical Support' AND specialization = 'Technical') OR
        (team_name = 'Billing Support' AND specialization = 'Billing')
    )
);

CREATE TABLE IF NOT EXISTS support_analytics.agents (
    agent_id TEXT PRIMARY KEY CHECK (agent_id ~ '^AG[0-9]+$'),
    agent_label TEXT NOT NULL CHECK (agent_label ~ '^Synthetic Agent [0-9]+$'),
    team_id TEXT NOT NULL REFERENCES support_analytics.teams(team_id),
    hired_at TIMESTAMPTZ NOT NULL,
    experience_level TEXT NOT NULL CHECK (experience_level IN ('Junior', 'Intermediate', 'Senior')),
    CONSTRAINT agents_id_team_unique UNIQUE (agent_id, team_id)
);

CREATE TABLE IF NOT EXISTS support_analytics.tickets (
    ticket_id TEXT PRIMARY KEY CHECK (ticket_id ~ '^TK[0-9]+$'),
    customer_id TEXT NOT NULL REFERENCES support_analytics.customers(customer_id),
    priority TEXT NOT NULL CHECK (priority IN ('Critical', 'High', 'Medium', 'Low')),
    category TEXT NOT NULL CHECK (category IN ('Account', 'Technical', 'Billing', 'General')),
    channel TEXT NOT NULL CHECK (channel IN ('Email', 'Chat', 'Phone', 'Web')),
    status TEXT NOT NULL CHECK (status IN ('Open', 'In Progress', 'Pending', 'Resolved', 'Closed')),
    created_at TIMESTAMPTZ NOT NULL,
    first_response_at TIMESTAMPTZ,
    initial_resolved_at TIMESTAMPTZ,
    reopened_at TIMESTAMPTZ,
    reopen_count SMALLINT NOT NULL CHECK (reopen_count IN (0, 1)),
    resolved_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    current_agent_id TEXT NOT NULL,
    current_team_id TEXT NOT NULL REFERENCES support_analytics.teams(team_id),
    response_target_minutes INTEGER NOT NULL CHECK (response_target_minutes > 0),
    resolution_target_minutes INTEGER NOT NULL CHECK (resolution_target_minutes > 0),
    response_deadline TIMESTAMPTZ NOT NULL,
    resolution_deadline TIMESTAMPTZ NOT NULL,
    response_sla_status TEXT NOT NULL CHECK (response_sla_status IN ('Met', 'Breached', 'Pending')),
    resolution_sla_status TEXT NOT NULL CHECK (resolution_sla_status IN ('Met', 'Breached', 'Pending')),
    overall_sla_status TEXT NOT NULL CHECK (overall_sla_status IN ('Met', 'Breached', 'Pending')),
    CONSTRAINT tickets_agent_team_fk FOREIGN KEY (current_agent_id, current_team_id)
        REFERENCES support_analytics.agents(agent_id, team_id),
    CONSTRAINT tickets_id_customer_unique UNIQUE (ticket_id, customer_id),
    CONSTRAINT tickets_policy_fk
        FOREIGN KEY (priority, response_target_minutes, resolution_target_minutes)
        REFERENCES support_analytics.sla_policies
            (priority, response_target_minutes, resolution_target_minutes),
    CONSTRAINT tickets_deadlines_match CHECK (
        response_deadline = created_at + make_interval(mins => response_target_minutes) AND
        resolution_deadline = created_at + make_interval(mins => resolution_target_minutes)
    ),
    CONSTRAINT tickets_status_events_match CHECK (
        (status = 'Open') = (first_response_at IS NULL) AND
        (status IN ('Resolved', 'Closed')) = (resolved_at IS NOT NULL) AND
        (status = 'Closed') = (closed_at IS NOT NULL)
    ),
    CONSTRAINT tickets_event_order CHECK (
        (first_response_at IS NULL OR first_response_at >= created_at) AND
        (initial_resolved_at IS NULL OR (first_response_at IS NOT NULL AND initial_resolved_at >= first_response_at)) AND
        (reopened_at IS NULL OR (initial_resolved_at IS NOT NULL AND reopened_at > initial_resolved_at)) AND
        (resolved_at IS NULL OR (initial_resolved_at IS NOT NULL AND resolved_at >= initial_resolved_at)) AND
        (reopened_at IS NULL OR resolved_at IS NULL OR resolved_at > reopened_at) AND
        (closed_at IS NULL OR (resolved_at IS NOT NULL AND closed_at >= resolved_at))
    ),
    CONSTRAINT tickets_reopen_match CHECK (
        (reopen_count = 1) = (reopened_at IS NOT NULL) AND
        (reopen_count = 1 OR initial_resolved_at IS NOT DISTINCT FROM resolved_at)
    ),
    CONSTRAINT tickets_overall_sla_match CHECK (
        overall_sla_status = CASE
            WHEN response_sla_status = 'Breached' OR resolution_sla_status = 'Breached' THEN 'Breached'
            WHEN response_sla_status = 'Met' AND resolution_sla_status = 'Met' THEN 'Met'
            ELSE 'Pending'
        END
    )
);

CREATE TABLE IF NOT EXISTS support_analytics.assignment_history (
    assignment_id TEXT PRIMARY KEY CHECK (assignment_id ~ '^AS[0-9]+$'),
    ticket_id TEXT NOT NULL REFERENCES support_analytics.tickets(ticket_id),
    agent_id TEXT NOT NULL,
    team_id TEXT NOT NULL,
    assigned_at TIMESTAMPTZ NOT NULL,
    unassigned_at TIMESTAMPTZ,
    assignment_reason TEXT NOT NULL CHECK (assignment_reason IN ('Initial', 'Reassignment', 'Reopened')),
    CONSTRAINT assignment_agent_team_fk FOREIGN KEY (agent_id, team_id)
        REFERENCES support_analytics.agents(agent_id, team_id),
    CONSTRAINT assignment_positive_interval CHECK (unassigned_at IS NULL OR unassigned_at > assigned_at),
    CONSTRAINT assignment_ticket_start_unique UNIQUE (ticket_id, assigned_at)
);

CREATE TABLE IF NOT EXISTS support_analytics.customer_feedback (
    feedback_id TEXT PRIMARY KEY CHECK (feedback_id ~ '^FB[0-9]+$'),
    ticket_id TEXT NOT NULL UNIQUE,
    customer_id TEXT NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL,
    csat_score SMALLINT NOT NULL CHECK (csat_score BETWEEN 1 AND 5),
    CONSTRAINT feedback_ticket_customer_fk FOREIGN KEY (ticket_id, customer_id)
        REFERENCES support_analytics.tickets(ticket_id, customer_id)
);

-- Primary keys, unique constraints, and foreign keys above also supply some
-- indexes. These additions target common filters and range/grouping queries.
CREATE INDEX IF NOT EXISTS ix_agents_team ON support_analytics.agents (team_id);
CREATE INDEX IF NOT EXISTS ix_tickets_created_at ON support_analytics.tickets (created_at);
CREATE INDEX IF NOT EXISTS ix_tickets_priority_created ON support_analytics.tickets (priority, created_at);
CREATE INDEX IF NOT EXISTS ix_tickets_customer ON support_analytics.tickets (customer_id);
CREATE INDEX IF NOT EXISTS ix_tickets_team_status ON support_analytics.tickets (current_team_id, status);
CREATE INDEX IF NOT EXISTS ix_tickets_unresolved_created ON support_analytics.tickets (created_at) WHERE resolved_at IS NULL;
CREATE INDEX IF NOT EXISTS ix_tickets_resolution_sla ON support_analytics.tickets (resolution_sla_status, priority);
CREATE UNIQUE INDEX IF NOT EXISTS ux_assignment_one_current
    ON support_analytics.assignment_history (ticket_id) WHERE unassigned_at IS NULL;
CREATE INDEX IF NOT EXISTS ix_assignment_agent_time ON support_analytics.assignment_history (agent_id, assigned_at);
CREATE INDEX IF NOT EXISTS ix_assignment_ticket_reason ON support_analytics.assignment_history (ticket_id, assignment_reason);
