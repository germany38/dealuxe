CREATE TABLE "referrals" (
	"id" serial PRIMARY KEY,
	"referrer_id" integer NOT NULL,
	"referee_id" integer NOT NULL UNIQUE,
	"referrer_points" integer DEFAULT 50 NOT NULL,
	"referee_points" integer DEFAULT 25 NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "users" ADD COLUMN "referral_code" text;--> statement-breakpoint
ALTER TABLE "users" ADD COLUMN "referred_by" integer;--> statement-breakpoint
ALTER TABLE "users" ADD CONSTRAINT "users_referral_code_key" UNIQUE("referral_code");--> statement-breakpoint
CREATE INDEX "referrals_referrer_id_idx" ON "referrals" ("referrer_id");--> statement-breakpoint
ALTER TABLE "referrals" ADD CONSTRAINT "referrals_referrer_id_users_id_fkey" FOREIGN KEY ("referrer_id") REFERENCES "users"("id");--> statement-breakpoint
ALTER TABLE "referrals" ADD CONSTRAINT "referrals_referee_id_users_id_fkey" FOREIGN KEY ("referee_id") REFERENCES "users"("id");--> statement-breakpoint
ALTER TABLE "users" ADD CONSTRAINT "users_referred_by_users_id_fkey" FOREIGN KEY ("referred_by") REFERENCES "users"("id");