/** A hard-coded stand-in for the reading, until the Reading API exists.
 *
 * The chat screen shows the reading beside the conversation, but no endpoint
 * serves reading text yet. This is the real `strategy` reading from the seed —
 * text and core components both — so the split screen is faithful, not lorem
 * ipsum. `id` is the deterministic seed id (see scripts/seed.py `reading_id`),
 * so starting a session with it hits a real row that exists after `seed.py`.
 *
 * When feat/reading-api lands, this whole module is replaced by a fetch keyed on
 * the reading chosen from the list. Nothing else in the tutoring screen changes:
 * it already reads `title`, `content` and `coreComponents` as props. */

export const DEV_READING = {
  id: "2adf075f-8d77-5a76-b586-1e7c5272bd64",
  title: "Strategy",
  // The class this session belongs to. Placeholder until the reading-list flow
  // carries real class context; shown beside the title, as in the mockup.
  section: "STSWENG S12",
  coreComponents: [
    "A company's strategy is the coordinated set of actions that its managers take to outperform the company's competitors and achieve superior profitability.",
  ],
  content: `A company's strategy is the coordinated set of actions that its managers take to outperform the company's competitors and achieve superior profitability. The objective of a well-crafted strategy is not merely temporary competitive success and profits in the short run, but rather the sort of lasting success that can support growth and secure the company's future over the long term. Achieving this entails making a managerial commitment to a coherent array of well-considered choices about how to compete.

These include choices about:
• How to create products or services that attract and please customers.
• How to position the company in the industry.
• How to develop and deploy resources to build valuable competitive capabilities.
• How each functional piece of the business (R&D, supply chain activities, production, sales and marketing, distribution, finance, and human resources) will be operated.
• How to achieve the company's performance targets.

In most industries, companies have considerable freedom in choosing the hows of strategy. Thus some rivals strive to create superior value for customers by achieving lower costs than rivals, while others pursue product superiority or personalized customer service or the development of capabilities that rivals cannot match. Some competitors position themselves in only one part of the industry's chain of production/distribution activities, while others are partially or fully integrated, with operations ranging from components production to manufacturing and assembly to wholesale distribution or retailing. Some competitors deliberately confine their operations to local or regional markets; others opt to compete nationally, internationally, or globally. Some companies decide to operate in only one industry, while others diversify broadly or narrowly, into related or unrelated industries.`,
};
