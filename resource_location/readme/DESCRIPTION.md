Shared "location" concept for resource apps: a location is a
`res.partner` flagged as a resource work site, giving name, address,
timezone and geo coordinates for free.

Also provides **presence lines** (`resource.location.presence`): which
locations a resource is available at, and on what calendar. A line
with no calendar means the resource is always at that location; a
resource with no lines at all is available anywhere. The first line
by sequence covering an instant wins when several overlap.

Used by Resource Reservation (bookable sites + per-location
availability) and Resource Planning (service post sites), so the same
site and the same presence semantics are defined once and seen by
both apps.
