type Props = {
  value: string
  onChange: (value: string) => void
}

export default function ApiKeyInput({ value, onChange }: Props) {
  return (
    <label className="field">
      <span>API Key</span>
      <input
        type="password"
        placeholder="Paste API key"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  )
}
