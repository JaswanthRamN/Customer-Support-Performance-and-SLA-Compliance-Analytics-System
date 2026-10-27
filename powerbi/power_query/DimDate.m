let
    MinimumDate = Date.StartOfYear(List.Min(FactTickets[created_date])),
    MaximumDate = Date.EndOfYear(Date.From(DateTimeZone.SwitchZone(pAnalysisAsOfUtc, 0))),
    Dates = List.Dates(MinimumDate, Duration.Days(MaximumDate - MinimumDate) + 1, #duration(1, 0, 0, 0)),
    ToTable = Table.FromList(Dates, Splitter.SplitByNothing(), {"Date"}),
    Typed = Table.TransformColumnTypes(ToTable, {{"Date", type date}}),
    AddedDateKey = Table.AddColumn(Typed, "DateKey", each
        Date.Year([Date]) * 10000 + Date.Month([Date]) * 100 + Date.Day([Date]), Int64.Type),
    AddedYear = Table.AddColumn(AddedDateKey, "Year", each Date.Year([Date]), Int64.Type),
    AddedQuarter = Table.AddColumn(AddedYear, "Quarter", each "Q" & Text.From(Date.QuarterOfYear([Date])), type text),
    AddedMonthNumber = Table.AddColumn(AddedQuarter, "MonthNumber", each Date.Month([Date]), Int64.Type),
    AddedMonth = Table.AddColumn(AddedMonthNumber, "Month", each Date.MonthName([Date]), type text),
    AddedYearMonth = Table.AddColumn(AddedMonth, "YearMonth", each Date.ToText([Date], "yyyy-MM"), type text),
    AddedWeekStart = Table.AddColumn(AddedYearMonth, "WeekStartMonday", each Date.StartOfWeek([Date], Day.Monday), type date),
    AddedDay = Table.AddColumn(AddedWeekStart, "Day", each Date.Day([Date]), Int64.Type),
    Sorted = Table.Sort(AddedDay, {{"Date", Order.Ascending}})
in
    Sorted
