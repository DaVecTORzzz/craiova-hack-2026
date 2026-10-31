// Which operator action is allowed from which status. Mirrors ACTIONS in
// backend/app/services/events.py; anything else gets a 409 from the API.
const ALLOWED_FROM = {
  ack: ['open', 'escalated'],
  false_positive: ['open', 'escalated', 'acknowledged'],
  reopen: ['acknowledged', 'false_positive', 'escalated', 'resolved'],
};

export function canDo(action, status) {
  return Boolean(ALLOWED_FROM[action]?.includes(status));
}
