CREATE TABLE "coin_purchases" (
	"id" serial PRIMARY KEY,
	"user_id" integer NOT NULL,
	"stripe_session_id" text NOT NULL UNIQUE,
	"bundle_key" text NOT NULL,
	"coins" integer NOT NULL,
	"amount_cents" integer NOT NULL,
	"status" text DEFAULT 'pending' NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"completed_at" timestamp
);
--> statement-breakpoint
CREATE TABLE "comment_likes" (
	"id" serial PRIMARY KEY,
	"comment_id" integer NOT NULL,
	"user_id" integer NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "comments" (
	"id" serial PRIMARY KEY,
	"post_slug" text NOT NULL,
	"user_id" integer NOT NULL,
	"body" text DEFAULT '' NOT NULL,
	"gift_key" text,
	"gift_coins" integer DEFAULT 0 NOT NULL,
	"like_count" integer DEFAULT 0 NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "point_events" (
	"id" serial PRIMARY KEY,
	"user_id" integer NOT NULL,
	"kind" text NOT NULL,
	"target_key" text NOT NULL,
	"base_points" integer NOT NULL,
	"multiplier" integer DEFAULT 1 NOT NULL,
	"points" integer NOT NULL,
	"day" text NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "users" ADD COLUMN "coins" integer DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE "users" ADD COLUMN "streak_days" integer DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE "users" ADD COLUMN "last_active_date" text;--> statement-breakpoint
CREATE INDEX "coin_purchases_user_id_idx" ON "coin_purchases" ("user_id");--> statement-breakpoint
CREATE UNIQUE INDEX "comment_likes_comment_user_idx" ON "comment_likes" ("comment_id","user_id");--> statement-breakpoint
CREATE INDEX "comments_post_slug_idx" ON "comments" ("post_slug","created_at");--> statement-breakpoint
CREATE INDEX "comments_user_id_idx" ON "comments" ("user_id");--> statement-breakpoint
CREATE UNIQUE INDEX "point_events_dedupe_idx" ON "point_events" ("user_id","kind","target_key","day");--> statement-breakpoint
CREATE INDEX "point_events_user_id_idx" ON "point_events" ("user_id");--> statement-breakpoint
ALTER TABLE "coin_purchases" ADD CONSTRAINT "coin_purchases_user_id_users_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id");--> statement-breakpoint
ALTER TABLE "comment_likes" ADD CONSTRAINT "comment_likes_comment_id_comments_id_fkey" FOREIGN KEY ("comment_id") REFERENCES "comments"("id");--> statement-breakpoint
ALTER TABLE "comment_likes" ADD CONSTRAINT "comment_likes_user_id_users_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id");--> statement-breakpoint
ALTER TABLE "comments" ADD CONSTRAINT "comments_user_id_users_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id");--> statement-breakpoint
ALTER TABLE "point_events" ADD CONSTRAINT "point_events_user_id_users_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id");