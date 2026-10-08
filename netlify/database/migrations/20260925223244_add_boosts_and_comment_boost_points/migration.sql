CREATE TABLE "boosts" (
	"id" serial PRIMARY KEY,
	"user_id" integer NOT NULL,
	"target_type" text NOT NULL,
	"target_key" text NOT NULL,
	"post_slug" text NOT NULL,
	"tier_key" text NOT NULL,
	"points" integer NOT NULL,
	"expires_at" timestamp NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "comments" ADD COLUMN "boost_points" integer DEFAULT 0 NOT NULL;--> statement-breakpoint
CREATE INDEX "boosts_target_idx" ON "boosts" ("target_type","target_key","expires_at");--> statement-breakpoint
CREATE INDEX "boosts_expires_at_idx" ON "boosts" ("expires_at");--> statement-breakpoint
CREATE INDEX "boosts_user_id_idx" ON "boosts" ("user_id");--> statement-breakpoint
ALTER TABLE "boosts" ADD CONSTRAINT "boosts_user_id_users_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id");