import ReactMarkdown from "react-markdown"
import rehypeSanitize from "rehype-sanitize"
import { cn } from "@/lib/utils"

/**
 * Renders Markdown for reading. Raw HTML in the source is not executed (react-markdown ignores it) and the
 * output is passed through rehype-sanitize as a second layer; links open in a new tab with no referrer.
 */
export function Markdown({ children, className }: { children: string; className?: string }) {
  return (
    <div className={cn("max-w-prose text-sm leading-relaxed [overflow-wrap:anywhere] [&>*+*]:mt-3 [&_a]:underline [&_a]:underline-offset-4 [&_blockquote]:border-l-2 [&_blockquote]:pl-3 [&_blockquote]:text-muted-foreground [&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_code]:py-0.5 [&_code]:text-[0.8125rem] [&_h1]:mt-6 [&_h1]:text-xl [&_h1]:font-semibold [&_h2]:mt-5 [&_h2]:text-lg [&_h2]:font-semibold [&_h3]:mt-4 [&_h3]:font-semibold [&_hr]:my-4 [&_li+li]:mt-1 [&_ol]:list-decimal [&_ol]:pl-5 [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:bg-muted [&_pre]:p-3 [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_table]:w-full [&_td]:border [&_td]:px-2 [&_td]:py-1 [&_th]:border [&_th]:bg-muted [&_th]:px-2 [&_th]:py-1 [&_th]:text-left [&_ul]:list-disc [&_ul]:pl-5", className)}>
      <ReactMarkdown
        rehypePlugins={[rehypeSanitize]}
        components={{ a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer nofollow">{children}</a> }}
      >
        {children}
      </ReactMarkdown>
    </div>
  )
}
