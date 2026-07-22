import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  users: defineTable({
    email: v.string(),
    name: v.optional(v.string()),
    image: v.optional(v.string()),
    role: v.union(v.literal("USER"), v.literal("PREMIUM"), v.literal("ADMIN")),
    emailVerified: v.boolean(),
    passwordHash: v.optional(v.string()),
    createdAt: v.number(),
    updatedAt: v.number(),
    lastLoginAt: v.optional(v.number()),
  }).index("by_email", ["email"]),

  profiles: defineTable({
    userId: v.id("users"),
    displayName: v.optional(v.string()),
    avatarUrl: v.optional(v.string()),
    timezone: v.optional(v.string()),
    createdAt: v.number(),
    updatedAt: v.number(),
  }).index("by_user", ["userId"]),

  sessions: defineTable({
    userId: v.id("users"),
    tokenHash: v.string(),
    deviceId: v.optional(v.id("devices")),
    ipAddress: v.optional(v.string()),
    userAgent: v.optional(v.string()),
    expiresAt: v.number(),
    lastSeenAt: v.number(),
    createdAt: v.number(),
  }).index("by_user", ["userId"]).index("by_token", ["tokenHash"]),

  devices: defineTable({
    userId: v.id("users"),
    name: v.string(),
    fingerprint: v.string(),
    ipAddress: v.optional(v.string()),
    userAgent: v.optional(v.string()),
    lastSeenAt: v.number(),
    trusted: v.boolean(),
    createdAt: v.number(),
  }).index("by_user", ["userId"]).index("by_fingerprint", ["fingerprint"]),

  accounts: defineTable({
    userId: v.optional(v.id("users")),
    slug: v.string(),
    name: v.string(),
    username: v.optional(v.string()),
    platform: v.optional(v.string()),
    status: v.optional(v.string()),
    createdAt: v.number(),
    updatedAt: v.number(),
    lastSeenLiveAt: v.optional(v.number()),
  }).index("by_slug", ["slug"]).index("by_user", ["userId"]),

  recordings: defineTable({
    userId: v.optional(v.id("users")),
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
    privacy: v.union(v.literal("private"), v.literal("shared"), v.literal("team")),
    contentHash: v.optional(v.string()),
    expiresAt: v.optional(v.number()),
  }).index("by_slug", ["slug"]).index("by_user", ["userId"]),

  videoPermissions: defineTable({
    videoId: v.id("recordings"),
    ownerId: v.id("users"),
    subjectUserId: v.optional(v.id("users")),
    permission: v.union(v.literal("view"), v.literal("download"), v.literal("edit")),
    expiresAt: v.optional(v.number()),
    createdAt: v.number(),
  }).index("by_video", ["videoId"]).index("by_owner", ["ownerId"]),

  subscriptions: defineTable({
    userId: v.id("users"),
    plan: v.union(v.literal("FREE"), v.literal("PREMIUM"), v.literal("ADMIN")),
    status: v.string(),
    currentPeriodEnd: v.optional(v.number()),
    createdAt: v.number(),
    updatedAt: v.number(),
  }).index("by_user", ["userId"]),

  usageLimits: defineTable({
    userId: v.id("users"),
    storageLimitBytes: v.number(),
    storageUsedBytes: v.number(),
    aiCredits: v.number(),
    aiUsed: v.number(),
    updatedAt: v.number(),
  }).index("by_user", ["userId"]),

  auditLogs: defineTable({
    userId: v.optional(v.id("users")),
    action: v.string(),
    resourceType: v.optional(v.string()),
    resourceId: v.optional(v.string()),
    metadata: v.optional(v.any()),
    ipAddress: v.optional(v.string()),
    userAgent: v.optional(v.string()),
    createdAt: v.number(),
  }).index("by_user", ["userId"]).index("by_created", ["createdAt"]),

  apiKeys: defineTable({
    userId: v.id("users"),
    name: v.string(),
    keyHash: v.string(),
    lastUsedAt: v.optional(v.number()),
    revokedAt: v.optional(v.number()),
    createdAt: v.number(),
  }).index("by_user", ["userId"]).index("by_hash", ["keyHash"]),

  notifications: defineTable({
    userId: v.id("users"),
    type: v.string(),
    title: v.string(),
    message: v.string(),
    readAt: v.optional(v.number()),
    createdAt: v.number(),
  }).index("by_user", ["userId"]).index("by_created", ["createdAt"]),
});
