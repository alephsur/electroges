import { create } from 'zustand'
import dayjs from 'dayjs'

type CalendarView = 'month' | 'week'

interface CalendarStore {
  currentDate: dayjs.Dayjs
  view: CalendarView
  selectedDate: string | null
  setCurrentDate: (d: dayjs.Dayjs) => void
  setView: (v: CalendarView) => void
  setSelectedDate: (d: string | null) => void
  goToToday: () => void
  goToPrev: () => void
  goToNext: () => void
}

export const useCalendarStore = create<CalendarStore>((set, get) => ({
  currentDate: dayjs(),
  view: 'month',
  selectedDate: null,

  setCurrentDate: (d) => set({ currentDate: d }),
  setView: (v) => set({ view: v }),
  setSelectedDate: (d) => set({ selectedDate: d }),

  goToToday: () => set({ currentDate: dayjs() }),
  goToPrev: () => {
    const { currentDate, view } = get()
    set({ currentDate: view === 'month' ? currentDate.subtract(1, 'month') : currentDate.subtract(1, 'week') })
  },
  goToNext: () => {
    const { currentDate, view } = get()
    set({ currentDate: view === 'month' ? currentDate.add(1, 'month') : currentDate.add(1, 'week') })
  },
}))
