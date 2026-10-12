// Every feature in the left rail, with the details + workflow shown in the right panel.
import {
  MessageSquareText, Radar, Database, Users, Share2, Plug, Sparkles, type LucideIcon,
} from "lucide-react";

export type Feature = {
  href: string;
  name: string;
  icon: LucideIcon;
  tagline: string;
  details: string;
  workflow: { title: string; text: string }[];
  powered: string[];
};

export const FEATURES: Feature[] = [
  {
    href: "/",
    name: "Ask the Brain",
    icon: MessageSquareText,
    tagline: "Answers with who owns it and what breaks",
    details:
      "Ask in plain language. WhyBot searches every document, follows relationships across them, and adapts the answer to who is asking. Compare mode puts plain search next to graph-powered answers.",
    workflow: [
      { title: "Ask", text: "Type a question or pick a suggestion." },
      { title: "Retrieve", text: "Hybrid search finds the most relevant passages." },
      { title: "Connect", text: "The context graph links people, services, decisions and incidents." },
      { title: "Personalize", text: "Your persona's memories shape depth and focus." },
      { title: "Answer", text: "The LLM writes a cited answer and draws the relationship map." },
    ],
    powered: ["Hybrid search", "Context graph", "Thinking mode", "Memories (type=all)"],
  },
  {
    href: "/impact",
    name: "Blast Radius",
    icon: Radar,
    tagline: "What breaks before you ship a change",
    details:
      "Describe a planned change — deprecating an API, a reorg, someone going on leave. WhyBot walks HydraDB's graph hop by hop to find everything affected, the owners to notify, and past incidents that went wrong, then scores the risk and drafts the heads-up messages.",
    workflow: [
      { title: "Describe", text: "Type the change you're planning." },
      { title: "Locate", text: "Match it to entities in the knowledge graph." },
      { title: "Traverse", text: "Walk dependencies outward, up to 3 hops." },
      { title: "Recall", text: "Pull past incidents and decisions touching those entities." },
      { title: "Score", text: "Rate risk from reach, owners and incident history." },
      { title: "Notify", text: "Draft a heads-up for every owning team." },
    ],
    powered: ["Context graph", "Multi-hop traversal", "Bring-your-own-graph", "Memories"],
  },
  {
    href: "/knowledge",
    name: "Knowledge",
    icon: Database,
    tagline: "Feed the brain your files and docs",
    details:
      "Drop PDFs, notes, Slack or Jira exports, or paste any public docs URL. HydraDB chunks, embeds and extracts entities and relationships automatically.",
    workflow: [
      { title: "Add", text: "Drag files in or paste a URL." },
      { title: "Extract", text: "Text is pulled from PDFs and web pages." },
      { title: "Ingest", text: "Content is sent to HydraDB as shared knowledge." },
      { title: "Index", text: "Status moves queued → processing → graph_creation → completed." },
      { title: "Ready", text: "Graph-powered answers switch on once indexing completes." },
    ],
    powered: ["Knowledge ingestion", "Auto graph extraction", "Indexing status API"],
  },
  {
    href: "/personas",
    name: "Personas & Memory",
    icon: Users,
    tagline: "Same question, answer tailored to the asker",
    details:
      "Each persona is its own HydraDB memory collection. At query time it is merged with company knowledge, so an engineer gets steps and a manager gets timelines and owners.",
    workflow: [
      { title: "Choose", text: "Pick a role or create your own persona." },
      { title: "Remember", text: "Add facts like 'I own the mobile release'." },
      { title: "Store", text: "Facts are saved to the persona's memory collection." },
      { title: "Merge", text: "Queries blend memories with shared knowledge by relevance." },
    ],
    powered: ["Memories", "Per-persona collections", "type='all' queries"],
  },
  {
    href: "/graph",
    name: "Graph Explorer",
    icon: Share2,
    tagline: "See how your company is connected",
    details:
      "Every relationship WhyBot has discovered, in one interactive map. Drag nodes, zoom, and search for a person, service or decision to see its neighbourhood.",
    workflow: [
      { title: "Discover", text: "Each graph answer contributes relationship paths." },
      { title: "Declare", text: "Structured data (org charts, service catalogs) adds exact edges." },
      { title: "Explore", text: "Filter by name and follow connections visually." },
    ],
    powered: ["Context graphs", "Bring-your-own-graph"],
  },
  {
    href: "/integrations",
    name: "API & Integrations",
    icon: Plug,
    tagline: "Plug the brain into anything",
    details:
      "A clean REST API so the brain can power a Slack bot, an App-Starter SaaS frontend, an IDE plugin or an internal portal. Try requests live from this page.",
    workflow: [
      { title: "Pick", text: "Choose an endpoint." },
      { title: "Send", text: "Run it live against your brain." },
      { title: "Embed", text: "Copy the snippet into your app or bot." },
    ],
    powered: ["REST API", "App-Starter ready"],
  },
  {
    href: "/about",
    name: "Built With",
    icon: Sparkles,
    tagline: "HydraDB · App-Starter · Digo",
    details:
      "WhyBot is built on HydraDB's memory layer with a FastAPI engine and this Next.js frontend. It was made at the Company Brain Hackathon hosted by Digo.",
    workflow: [
      { title: "Store", text: "HydraDB holds knowledge, graph and memories." },
      { title: "Reason", text: "Claude or GPT writes cited answers." },
      { title: "Ship", text: "App-Starter adds auth, billing and workspaces." },
    ],
    powered: ["HydraDB", "Claude", "Next.js", "FastAPI"],
  },
];

export const featureFor = (path: string) =>
  FEATURES.find((f) => (f.href === "/" ? path === "/" : path.startsWith(f.href))) ?? FEATURES[0];
