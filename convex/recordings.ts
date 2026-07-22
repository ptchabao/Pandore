import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const list = query(async ({ db }) => {
  return await db.query("recordings").order("desc").collect();
});

export const upsert = mutation({
  args: {
    slug: v.string(),
    accountSlug: v.optional(v.string()),
    title: v.string(),
    filePath: v.string(),
    fileName: v.string(),
    status: v.string(),
    storageUrl: v.optional(v.string()),
    storageId: v.optional(v.string()),
    deletedFromServer: v.optional(v.boolean()),
    metadata: v.optional(v.any()),
  },
  handler: async ({ db }, args) => {
    const now = Date.now();
    const existing = await db
      .query("recordings")
      .withIndex("by_slug", (q) => q.eq("slug", args.slug))
      .first();

    if (existing) {
      await db.patch(existing._id, {
        ...args,
        updatedAt: now,
      });
      return existing._id;
    }

    await db.insert("recordings", {
      ...args,
      createdAt: now,
      updatedAt: now,
      uploadedAt: args.status === "uploaded" ? now : undefined,
      deletedFromServer: args.deletedFromServer ?? false,
    });
    return null;
  },
});

export const markUploaded = mutation({
  args: {
    slug: v.string(),
    storageId: v.string(),
    storageUrl: v.string(),
    deletedFromServer: v.optional(v.boolean()),
  },
  handler: async ({ db }, args) => {
    const existing = await db
      .query("recordings")
      .withIndex("by_slug", (q) => q.eq("slug", args.slug))
      .first();

    if (!existing) {
      throw new Error(`Recording not found for slug ${args.slug}`);
    }

    await db.patch(existing._id, {
      storageId: args.storageId,
      storageUrl: args.storageUrl,
      status: "uploaded",
      uploadedAt: Date.now(),
      deletedFromServer: args.deletedFromServer ?? false,
      updatedAt: Date.now(),
    });

    return existing._id;
  },
});
