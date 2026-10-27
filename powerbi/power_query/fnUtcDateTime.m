(value as any) as nullable datetime =>
let
    Result =
        if value = null then
            null
        else
            DateTimeZone.RemoveZone(DateTimeZone.SwitchZone(DateTimeZone.From(value), 0))
in
    Result
