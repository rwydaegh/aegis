import 'katex/dist/katex.min.css'
import { InlineMath } from 'react-katex'

interface TexProps {
  math: string
}

export default function Tex({ math }: TexProps) {
  return <InlineMath math={math} />
}
