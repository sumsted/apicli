import { xml } from '@codemirror/lang-xml'
import { json } from '@codemirror/lang-json'
import { oneDark } from '@codemirror/theme-one-dark'
import { EditorState } from '@codemirror/state'
import { EditorView, placeholder } from '@codemirror/view'
import { basicSetup } from 'codemirror'
import { useEffect, useRef } from 'react'

export type EditorLanguage = 'json' | 'xml' | 'text'

interface CodeEditorProps {
  value: string
  onChange?: (value: string) => void
  language?: EditorLanguage
  readOnly?: boolean
  placeholderText?: string
}

const transparent = EditorView.theme({
  '&': { backgroundColor: 'transparent', height: '100%' },
  '.cm-scroller': { fontFamily: 'inherit' },
  '.cm-content': { padding: '8px 0' },
  '&.cm-focused': { outline: 'none' },
})

export function CodeEditor({
  value,
  onChange,
  language = 'text',
  readOnly = false,
  placeholderText,
}: CodeEditorProps) {
  const host = useRef<HTMLDivElement>(null)
  const viewRef = useRef<EditorView | null>(null)
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

  useEffect(() => {
    if (!host.current) return

    const extensions = [
      basicSetup,
      oneDark,
      transparent,
      EditorView.lineWrapping,
      EditorState.readOnly.of(readOnly),
      EditorView.editable.of(!readOnly),
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          onChangeRef.current?.(update.state.doc.toString())
        }
      }),
    ]
    if (language === 'json') extensions.push(json())
    if (language === 'xml') extensions.push(xml())
    if (placeholderText) extensions.push(placeholder(placeholderText))

    const view = new EditorView({
      state: EditorState.create({ doc: value, extensions }),
      parent: host.current,
    })
    viewRef.current = view
    return () => {
      view.destroy()
      viewRef.current = null
    }
    // Rebuild when the language or read-only mode changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language, readOnly])

  useEffect(() => {
    const view = viewRef.current
    if (!view) return
    const current = view.state.doc.toString()
    if (current !== value) {
      view.dispatch({
        changes: { from: 0, to: current.length, insert: value },
      })
    }
  }, [value])

  return <div ref={host} className="h-full overflow-auto" />
}
