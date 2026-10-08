CREATE TABLE "daily_reveals" (
	"id" serial PRIMARY KEY,
	"user_id" integer NOT NULL,
	"reveal_date" text NOT NULL,
	"count" integer DEFAULT 0 NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "users" (
	"id" serial PRIMARY KEY,
	"netlify_id" text NOT NULL UNIQUE,
	"email" text NOT NULL UNIQUE,
	"tier" text DEFAULT 'free' NOT NULL,
	"stripe_customer_id" text,
	"stripe_subscription_id" text,
	"subscription_status" text,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX "daily_reveals_user_date_idx" ON "daily_reveals" ("user_id","reveal_date");--> statement-breakpoint
ALTER TABLE "daily_reveals" ADD CONSTRAINT "daily_reveals_user_id_users_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id");