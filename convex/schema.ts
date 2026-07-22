import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  accounts: defineTable({
    slug: v.string(),
    name: v.string(),
    username: v.optional(v.string()),
    platform: v.optional(v.string()),
    status: v.optional(v.string()),
    createdAt: v.number(),
    updatedAt: v.number(),
    lastSeenLiveAt: v.optional(v.number()),
  }).index("by_slug", ["slug"]),

  recordings: defineTable({
    slug: v.string(),
    accountSlug: v.optional(v.string()),
    title: v.string(),
    filePath: v.string(),
    fileName: v.string(),
    storageUrl: v.optional(v.string()),
    storageId: v.optional(v.string()),
    status: v.string(),
    createdAt: v.number(),
    updatedAt: v.number(),
    uploadedAt: v.optional(v.number()),
    deletedFromServer: v.optional(v.boolean()),
    metadata: v.optional(v.any()),
  }).index("by_slug", ["slug"]),
});
