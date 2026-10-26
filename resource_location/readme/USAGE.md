Consumers read the presence map through
`resource.get_locations_on_period(start, end)`, which returns
`{resource_id: {location_id: Intervals}}` — the instants each
resource is present at each location. An empty inner map means
"present at any location".
