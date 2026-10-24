import type { LegalSection } from "./legal-page"

/** Written from how the product works today (Google sign-in, session cookies, Gmail connection, workspaces). ResolveAI is a non-commercial learning project. */
export const UPDATED = "October 24, 2026"

const CONTACT = "aadarshasubedi406@gmail.com"

export const TERMS = {
  title: "Terms of Service",
  intro: "ResolveAI is a non-commercial, educational capstone project built to learn how to design and run an AI-assisted support desk. It is not a commercial product. By creating an account or using it you agree to these terms.",
  sections: [
    { heading: "A learning project", body: ["ResolveAI is built for learning. It has no paying customers, no service-level commitments and no guarantees of any kind. Features, data and the whole service may change, be reset or be shut down at any time, with or without notice.", "Please do not store anything important or sensitive in it."] },
    { heading: "Your account", body: ["You sign in with a Google account. You are responsible for activity under your account and for keeping access to that Google account secure."] },
    { heading: "Workspaces and members", body: ["A workspace belongs to the people who created it. Owners decide who joins and what each member can do, and are responsible for what their members and their customers submit.", "Members can only see workspaces they belong to."] },
    { heading: "Your content", body: ["Tickets, replies, knowledge base articles and files you or your customers add remain yours. You allow ResolveAI to store, process and display them only as needed to run the project for you.", "Do not upload anything unlawful, anything you do not have the right to share, or malware."] },
    { heading: "Connected services", body: ["If you connect a Gmail account, ResolveAI reads mail (gmail.readonly) to create tickets and sends mail (gmail.send) to deliver replies, on that account only. You can disconnect it at any time from your workspace settings."] },
    { heading: "Acceptable use", body: ["Do not attempt to break, probe or overload the service, access data that is not yours, or use ResolveAI to send spam or abusive messages."] },
    { heading: "Ending your use", body: ["You can delete your account at any time. Deleted accounts are removed automatically from our system after a 7-day grace period. We may suspend or end access for breaking these terms."] },
    { heading: "No warranty", body: ["ResolveAI is provided as is, for learning purposes, without warranties of any kind. To the extent the law allows, the project owner is not liable for any loss arising from its use."] },
    { heading: "Contact", body: [`Questions about these terms go to ${CONTACT}.`] },
  ] satisfies LegalSection[],
}

export const PRIVACY = {
  title: "Privacy Policy",
  intro: "ResolveAI is a non-commercial, educational capstone project. This policy explains what it collects, why, and the choices you have. We collect only what the project needs and do not sell personal data.",
  sections: [
    { heading: "What we collect", body: ["From Google sign-in: your name, email address and profile picture.", "From your use: workspace details, tickets, replies, knowledge base articles and the files attached to them, plus basic activity records such as sign-ins and changes, kept in an audit log for your workspace.", "From a connected Gmail account: messages sent to the connected address and the replies sent from it."] },
    { heading: "How we use it", body: ["To run the project: signing you in, showing the right workspace, creating tickets from email, delivering replies and keeping an audit trail. We do not use your tickets or mail to advertise to you."] },
    { heading: "Google user data", body: ["If you connect Gmail, ResolveAI requests two scopes: gmail.readonly, to read incoming messages so they can become tickets, and gmail.send, to send your replies from your address. Gmail data is used only to provide these user-facing features.", "ResolveAI's use and transfer of information received from Google APIs to any other app adheres to the Google API Services User Data Policy, including the Limited Use requirements. Gmail data is not sold, not used for advertising, and not used to train generalized AI models. No person reads it except as needed for security, to comply with law, or with your consent."] },
    { heading: "Cookies", body: ["ResolveAI uses a session cookie to keep you signed in and a CSRF cookie to protect requests you make. We also remember your theme choice in your browser. We do not use advertising cookies."] },
    { heading: "Who sees your data", body: ["Members of a workspace see that workspace's data according to their role. Infrastructure providers that host the project process data on our behalf. We disclose data if the law requires it."] },
    { heading: "Retention and deletion", body: ["We keep data while your account or workspace is active. You can delete your account at any time; it is then removed automatically from our system after a 7-day grace period. Disconnecting Gmail removes the stored access tokens. Because this is a learning project, data may also be reset or wiped at any time.", `You can also email ${CONTACT} to ask to see, correct, export or delete your data.`] },
    { heading: "Security", body: ["Access uses signed-in sessions, workspace membership checks on every request, and encrypted connections. This is a learning project, so no system is guaranteed to be perfectly secure; sensitive actions are logged so they can be reviewed."] },
    { heading: "Changes and contact", body: [`We will post changes here and update the date above. Questions go to ${CONTACT}.`] },
  ] satisfies LegalSection[],
}
