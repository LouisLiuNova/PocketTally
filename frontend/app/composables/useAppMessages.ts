import {
  messageDuration,
  messageIsPersistent,
  MESSAGE_ICONS,
  type AppMessage,
} from '~/utils/messages'

const PERSISTENT_MESSAGES_KEY = 'pockettally-persistent-messages'

export function useAppMessages() {
  const toast = useToast()
  const persistent = useState<AppMessage[]>(PERSISTENT_MESSAGES_KEY, () => [])

  function push(message: AppMessage): AppMessage {
    if (messageIsPersistent(message)) {
      const index = persistent.value.findIndex(item => item.id === message.id)
      if (index === -1) {
        persistent.value = [...persistent.value, message]
      } else {
        persistent.value = persistent.value.map((item, itemIndex) => itemIndex === index ? message : item)
      }
      return message
    }

    toast.add({
      id: message.id,
      title: message.title,
      description: message.description,
      color: message.level,
      icon: MESSAGE_ICONS[message.level],
      duration: messageDuration(message),
      close: true,
      actions: message.action ? [{ label: message.action.label, onClick: message.action.onSelect }] : undefined,
    })
    return message
  }

  function dismiss(id: string) {
    persistent.value = persistent.value.filter(message => message.id !== id)
    toast.remove(id)
  }

  function clear() {
    persistent.value = []
    toast.clear()
  }

  return {
    persistent,
    push,
    add: push,
    dismiss,
    clear,
  }
}

export type AppMessages = ReturnType<typeof useAppMessages>
