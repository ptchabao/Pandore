import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const list = query(async ({ db }) => {
  return await db.query("accounts").order("asc").collect();
});

export const upsert = mutation({
  args: {
    slug: v.string(),
    name: v.string(),
    username: v.optional(v.string()),
    platform: v.optional(v.string()),
    status: v.optional(v.string()),
    lastSeenLiveAt: v.optional(v.number()),
  },
  handler: async ({ db }, args) => {
    const now = Date.now();
    const existing = await db
      .query("accounts")
      .withIndex("by_slug", (q) => q.eq("slug", args.slug))
      .first();

    if (existing) {
      await db.patch(existing._id, {
        ...args,
        updatedAt: now,
      });
      return existing._id;
    }

    await db.insert("accounts", {
      ...args,
      createdAt: now,
      updatedAt: now,
      status: args.status ?? "active",
    });
    return null;
  },
});
