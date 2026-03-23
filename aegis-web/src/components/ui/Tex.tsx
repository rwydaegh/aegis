import 'katex/dist/katex.min.css'
import katex from 'katex'

interface TexProps {
  math: string
}

export default function Tex({ math }: TexProps) {
  const html = katex.renderToString(math, { throwOnError: false })
  return <span dangerouslySetInnerHTML={{ __html: html }} />
}
