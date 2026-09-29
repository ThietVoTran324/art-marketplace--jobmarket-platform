import mitt from 'mitt'

/** App-wide UI events (save lists, etc.) */
export const bus = mitt()

/** Payload: { pinId: number, boardId: number | null } */
export const PIN_SAVED = 'pin-saved'
