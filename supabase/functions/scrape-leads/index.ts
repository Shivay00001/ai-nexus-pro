import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2.57.4";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Client-Info, Apikey",
};

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      status: 200,
      headers: corsHeaders,
    });
  }

  try {
    const { url } = await req.json();

    if (!url) {
      return new Response(
        JSON.stringify({ success: false, error: "URL is required" }),
        {
          status: 400,
          headers: {
            ...corsHeaders,
            "Content-Type": "application/json",
          },
        }
      );
    }

    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const supabase = createClient(supabaseUrl, supabaseKey);

    const jobId = crypto.randomUUID();
    await supabase.from("scraping_jobs").insert({
      id: jobId,
      url,
      status: "running",
    });

    let htmlContent = "";
    try {
      const response = await fetch(url, {
        headers: {
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        },
      });
      htmlContent = await response.text();
    } catch (error) {
      await supabase
        .from("scraping_jobs")
        .update({
          status: "failed",
          error_message: `Failed to fetch URL: ${error.message}`,
          completed_at: new Date().toISOString(),
        })
        .eq("id", jobId);

      return new Response(
        JSON.stringify({
          success: false,
          error: "Failed to fetch website",
        }),
        {
          status: 500,
          headers: {
            ...corsHeaders,
            "Content-Type": "application/json",
          },
        }
      );
    }

    const emails = extractEmails(htmlContent);
    const phones = extractPhones(htmlContent);
    const companyInfo = extractCompanyInfo(htmlContent);

    const { data: categories } = await supabase
      .from("categories")
      .select("*");

    const leads = [];

    if (emails.length > 0 || phones.length > 0) {
      const categoryId = categorizeLead(htmlContent, categories || []);

      for (let i = 0; i < Math.max(emails.length, phones.length, 1); i++) {
        const lead = {
          category_id: categoryId,
          company_name: companyInfo.name || extractDomainName(url),
          contact_name: "",
          email: emails[i] || "",
          phone: phones[i] || "",
          website: url,
          description: companyInfo.description || "",
          source_url: url,
          status: "new",
        };

        leads.push(lead);
      }
    } else {
      const categoryId = categorizeLead(htmlContent, categories || []);
      leads.push({
        category_id: categoryId,
        company_name: companyInfo.name || extractDomainName(url),
        contact_name: "",
        email: "",
        phone: "",
        website: url,
        description: companyInfo.description || "",
        source_url: url,
        status: "new",
      });
    }

    if (leads.length > 0) {
      await supabase.from("leads").insert(leads);
    }

    await supabase
      .from("scraping_jobs")
      .update({
        status: "completed",
        leads_found: leads.length,
        completed_at: new Date().toISOString(),
      })
      .eq("id", jobId);

    return new Response(
      JSON.stringify({
        success: true,
        leadsFound: leads.length,
      }),
      {
        headers: {
          ...corsHeaders,
          "Content-Type": "application/json",
        },
      }
    );
  } catch (error) {
    return new Response(
      JSON.stringify({
        success: false,
        error: error.message || "An unexpected error occurred",
      }),
      {
        status: 500,
        headers: {
          ...corsHeaders,
          "Content-Type": "application/json",
        },
      }
    );
  }
});

function extractEmails(html: string): string[] {
  const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
  const emails = html.match(emailRegex) || [];
  const uniqueEmails = [...new Set(emails)];
  return uniqueEmails
    .filter((email) => !email.match(/\.(png|jpg|jpeg|gif|svg|css|js|woff|ttf)$/i))
    .slice(0, 10);
}

function extractPhones(html: string): string[] {
  const phoneRegex = /(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/g;
  const phones = html.match(phoneRegex) || [];
  const uniquePhones = [...new Set(phones)];
  return uniquePhones.slice(0, 10);
}

function extractCompanyInfo(html: string): { name: string; description: string } {
  let name = "";
  let description = "";

  const titleMatch = html.match(/<title[^>]*>([^<]+)<\/title>/i);
  if (titleMatch) {
    name = titleMatch[1].trim();
  }

  const metaDescMatch = html.match(
    /<meta[^>]*name=["']description["'][^>]*content=["']([^"']+)["']/i
  );
  if (metaDescMatch) {
    description = metaDescMatch[1].trim();
  }

  const h1Match = html.match(/<h1[^>]*>([^<]+)<\/h1>/i);
  if (h1Match && !name) {
    name = h1Match[1].trim();
  }

  return { name, description };
}

function extractDomainName(url: string): string {
  try {
    const urlObj = new URL(url);
    let domain = urlObj.hostname.replace("www.", "");
    domain = domain.split(".")[0];
    return domain.charAt(0).toUpperCase() + domain.slice(1);
  } catch {
    return "Unknown Company";
  }
}

function categorizeLead(html: string, categories: any[]): string | null {
  const lowerHtml = html.toLowerCase();

  const categoryKeywords: Record<string, string[]> = {
    Technology: [
      "software",
      "saas",
      "app",
      "tech",
      "digital",
      "cloud",
      "api",
      "platform",
      "developer",
      "code",
      "programming",
    ],
    Healthcare: [
      "health",
      "medical",
      "hospital",
      "clinic",
      "doctor",
      "patient",
      "wellness",
      "care",
      "pharma",
    ],
    Finance: [
      "finance",
      "bank",
      "investment",
      "trading",
      "financial",
      "loan",
      "credit",
      "insurance",
      "wealth",
    ],
    "E-commerce": [
      "shop",
      "store",
      "ecommerce",
      "retail",
      "product",
      "cart",
      "checkout",
      "buy",
      "sell",
    ],
    Marketing: [
      "marketing",
      "advertising",
      "seo",
      "social media",
      "campaign",
      "brand",
      "agency",
      "creative",
    ],
    "Real Estate": [
      "real estate",
      "property",
      "realtor",
      "housing",
      "apartment",
      "rental",
      "mortgage",
    ],
    Education: [
      "education",
      "school",
      "university",
      "learning",
      "course",
      "training",
      "student",
      "teach",
    ],
    Manufacturing: [
      "manufacturing",
      "factory",
      "production",
      "industrial",
      "machinery",
      "equipment",
    ],
  };

  let bestMatch = null;
  let maxScore = 0;

  for (const category of categories) {
    const keywords = categoryKeywords[category.name] || [];
    let score = 0;

    for (const keyword of keywords) {
      const regex = new RegExp(keyword, "gi");
      const matches = lowerHtml.match(regex);
      if (matches) {
        score += matches.length;
      }
    }

    if (score > maxScore) {
      maxScore = score;
      bestMatch = category.id;
    }
  }

  if (!bestMatch) {
    const otherCategory = categories.find((c) => c.name === "Other");
    return otherCategory ? otherCategory.id : null;
  }

  return bestMatch;
}
