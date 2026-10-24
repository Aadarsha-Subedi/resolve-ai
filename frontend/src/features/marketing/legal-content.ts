import type { LegalSection } from "./legal-page"

/**
 * Draft text written from how the product works today (Google sign-in, session cookies, Gmail connection, workspaces).
 * Bracketed items are placeholders for the owner. Have a lawyer review before launch.
 */
export const UPDATED = "October 20, 2026"

export const TERMS = {
  title: "Terms of Service",
  intro: "These terms govern your use of ResolveAI, a support desk where customers file tickets and teams answer them. By creating an account or using the service you agree to them.",
  sections: [
    { heading: "Your account", body: ["You sign in with a Google account. You are responsible for activity under your account and for keeping access to that Google account secure.", "You must be allowed to enter a contract where you live, and if you use ResolveAI for an organization you confirm you can bind it to these terms."] },
    { heading: "Workspaces and members", body: ["A workspace belongs to the people who created it. Owners decide who joins and what each member can do. Owners are responsible for what their members and their customers submit.", "Members can only see workspaces they belong to."] },
    { heading: "Your content", body: ["Tickets, replies, knowledge base articles and files you or your customers add remain yours. You give ResolveAI the right to store, process and display them only as needed to run the service for you.", "You promise not to upload anything unlawful, anything you do not have the right to share, or malware."] },
    { heading: "Connected services", body: ["If you connect a Gmail account, ResolveAI reads and sends mail on that account only to create tickets and deliver replies. You can disconnect it at any time from your workspace settings."] },
    { heading: "Acceptable use", body: ["Do not attempt to break, probe or overload the service, access data that is not yours, or use ResolveAI to send spam or abusive messages."] },
    { heading: "Availability and changes", body: ["We work to keep ResolveAI available but do not promise it will always be uninterrupted or error free. We may change or remove features, and will give notice of changes that materially affect you."] },
    { heading: "Ending your use", body: ["You can stop using ResolveAI and ask for your workspace to be deleted at any time. We may suspend or end access for breaking these terms, with notice where we can give it."] },
    { heading: "Liability", body: ["To the extent the law allows, ResolveAI is provided as is, and our liability for any claim is limited to the amount you paid us in the 12 months before it. [Owner: confirm the limit and add jurisdiction-specific wording.]"] },
    { heading: "Governing law and contact", body: ["These terms are governed by the laws of [jurisdiction]. Questions go to [legal contact email]."] },
  ] satisfies LegalSection[],
}

export const PRIVACY = {
  title: "Privacy Policy",
  intro: "This policy explains what ResolveAI collects, why, and the choices you have. We collect what the service needs and do not sell personal data.",
  sections: [
    { heading: "What we collect", body: ["From Google sign-in: your name, email address and profile picture.", "From your use: workspace details, tickets, replies, knowledge base articles and the files attached to them, plus basic activity records such as sign-ins and changes, kept in an audit log for your workspace.", "From a connected Gmail account: messages sent to the connected address and the replies sent from it."] },
    { heading: "How we use it", body: ["To run the service: signing you in, showing the right workspace, creating tickets from email, delivering replies and keeping an audit trail. We do not use your tickets or mail to advertise to you."] },
    { heading: "Cookies", body: ["ResolveAI uses a session cookie to keep you signed in and a CSRF cookie to protect requests you make. We also remember your theme choice in your browser. We do not use advertising cookies."] },
    { heading: "Who sees your data", body: ["Members of a workspace see that workspace's data according to their role. Our infrastructure providers process data for us under agreements that limit their use. We disclose data if the law requires it. [Owner: list providers, for example hosting and email.]"] },
    { heading: "How long we keep it", body: ["We keep workspace data while the workspace is active. When a workspace is deleted we remove its data from live systems, and from backups within [retention period]."] },
    { heading: "Your choices", body: ["You can ask to see, correct, export or delete your personal data, and you can disconnect Gmail or leave a workspace at any time. Write to [privacy contact email] and we will respond within [response time]."] },
    { heading: "Security", body: ["Access uses signed-in sessions, workspace membership checks on every request, and encrypted connections. No system is perfectly secure, so we also log sensitive actions so they can be reviewed."] },
    { heading: "Changes and contact", body: ["We will post changes here and update the date above. Questions go to [privacy contact email]."] },
  ] satisfies LegalSection[],
}
