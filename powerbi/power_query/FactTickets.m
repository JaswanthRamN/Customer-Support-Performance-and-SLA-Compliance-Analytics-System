let
    Source = StagingDatabase{[Schema = "support_analytics", Item = "tickets"]}[Data],
    Selected = Table.SelectColumns(Source, {
        "ticket_id", "customer_id", "priority", "category", "channel", "status",
        "created_at", "first_response_at", "initial_resolved_at", "reopened_at",
        "reopen_count", "resolved_at", "closed_at", "current_agent_id", "current_team_id",
        "response_target_minutes", "resolution_target_minutes", "response_deadline",
        "resolution_deadline", "response_sla_status", "resolution_sla_status", "overall_sla_status"
    }),
    Typed = Table.TransformColumnTypes(Selected, {
        {"ticket_id", type text}, {"customer_id", type text}, {"priority", type text},
        {"category", type text}, {"channel", type text}, {"status", type text},
        {"reopen_count", Int64.Type}, {"current_agent_id", type text}, {"current_team_id", type text},
        {"response_target_minutes", Int64.Type}, {"resolution_target_minutes", Int64.Type},
        {"response_sla_status", type text}, {"resolution_sla_status", type text},
        {"overall_sla_status", type text}
    }),
    UtcTimestamps = Table.TransformColumns(Typed, {
        {"created_at", each fnUtcDateTime(_), type nullable datetime},
        {"first_response_at", each fnUtcDateTime(_), type nullable datetime},
        {"initial_resolved_at", each fnUtcDateTime(_), type nullable datetime},
        {"reopened_at", each fnUtcDateTime(_), type nullable datetime},
        {"resolved_at", each fnUtcDateTime(_), type nullable datetime},
        {"closed_at", each fnUtcDateTime(_), type nullable datetime},
        {"response_deadline", each fnUtcDateTime(_), type nullable datetime},
        {"resolution_deadline", each fnUtcDateTime(_), type nullable datetime}
    }),
    AddedCreatedDate = Table.AddColumn(UtcTimestamps, "created_date", each Date.From([created_at]), type date),
    AddedResponseHours = Table.AddColumn(AddedCreatedDate, "response_hours", each
        if [first_response_at] = null then null
        else Duration.TotalHours([first_response_at] - [created_at]), type nullable number),
    AddedResolutionHours = Table.AddColumn(AddedResponseHours, "resolution_hours", each
        if [resolved_at] = null then null
        else Duration.TotalHours([resolved_at] - [created_at]), type nullable number),
    AddedIsUnresolved = Table.AddColumn(AddedResolutionHours, "is_unresolved", each [resolved_at] = null, type logical),
    AddedUnresolvedAge = Table.AddColumn(AddedIsUnresolved, "unresolved_age_hours", each
        if [resolved_at] <> null then null
        else Duration.TotalHours(DateTimeZone.RemoveZone(DateTimeZone.SwitchZone(pAnalysisAsOfUtc, 0)) - [created_at]),
        type nullable number),
    AddedIsOverdue = Table.AddColumn(AddedUnresolvedAge, "is_overdue", each
        [resolved_at] = null and [resolution_sla_status] = "Breached", type logical),
    AddedIsReopened = Table.AddColumn(AddedIsOverdue, "is_reopened", each [reopen_count] > 0, type logical),
    AnalysisAsOfUtc = DateTimeZone.RemoveZone(DateTimeZone.SwitchZone(pAnalysisAsOfUtc, 0)),
    AddedAnalysisAsOf = Table.AddColumn(AddedIsReopened, "analysis_as_of_utc", each AnalysisAsOfUtc, type datetime),
    AddedResponseMinutesRemaining = Table.AddColumn(AddedAnalysisAsOf, "response_minutes_remaining_at_snapshot", each
        if [first_response_at] <> null then null
        else Duration.TotalMinutes([response_deadline] - AnalysisAsOfUtc), type nullable number),
    AddedResolutionMinutesRemaining = Table.AddColumn(AddedResponseMinutesRemaining, "resolution_minutes_remaining_at_snapshot", each
        if [resolved_at] <> null then null
        else Duration.TotalMinutes([resolution_deadline] - AnalysisAsOfUtc), type nullable number)
in
    AddedResolutionMinutesRemaining
