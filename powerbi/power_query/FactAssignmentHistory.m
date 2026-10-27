let
    Source = StagingDatabase{[Schema = "support_analytics", Item = "assignment_history"]}[Data],
    Selected = Table.SelectColumns(Source, {
        "assignment_id", "ticket_id", "agent_id", "team_id",
        "assigned_at", "unassigned_at", "assignment_reason"
    }),
    Typed = Table.TransformColumnTypes(Selected, {
        {"assignment_id", type text}, {"ticket_id", type text}, {"agent_id", type text},
        {"team_id", type text}, {"assignment_reason", type text}
    }),
    UtcTimestamps = Table.TransformColumns(Typed, {
        {"assigned_at", each fnUtcDateTime(_), type nullable datetime},
        {"unassigned_at", each fnUtcDateTime(_), type nullable datetime}
    }),
    AddedAssignedDate = Table.AddColumn(UtcTimestamps, "assigned_date", each Date.From([assigned_at]), type date),
    AddedIsCurrent = Table.AddColumn(AddedAssignedDate, "is_current_assignment", each [unassigned_at] = null, type logical),
    AddedRecordedInterval = Table.AddColumn(AddedIsCurrent, "recorded_interval_hours", each
        Duration.TotalHours(
            (if [unassigned_at] = null
             then DateTimeZone.RemoveZone(DateTimeZone.SwitchZone(pAnalysisAsOfUtc, 0))
             else [unassigned_at]) - [assigned_at]
        ), type number)
in
    AddedRecordedInterval
