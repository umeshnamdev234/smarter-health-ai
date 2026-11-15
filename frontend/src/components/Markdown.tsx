import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// react-markdown does not render raw HTML, so model output can't inject markup.
export default function Markdown({ text }: { text: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        table: ({ children }) => (
          <div className="tbl">
            <table>{children}</table>
          </div>
        ),
        a: ({ href, children }) => (
          <a href={href} target="_blank" rel="noreferrer noopener">
            {children}
          </a>
        ),
      }}
    >
      {text}
    </ReactMarkdown>
  );
}
