import { ScrapingResult, Category } from '../types';

const CORS_PROXIES = [
    'https://api.allorigins.win/get?url=',
    'https://api.codetabs.com/v1/proxy?quest=',
];

export async function scrapeWebsite(url: string): Promise<ScrapingResult> {
    let html = '';
    let lastError: Error | null = null;

    for (const proxy of CORS_PROXIES) {
        try {
            const proxyUrl = proxy + encodeURIComponent(url);
            const response = await fetch(proxyUrl);

            if (!response.ok) continue;

            const data = await response.json();
            html = typeof data === 'string' ? data : data.contents || '';

            if (html && html.length > 100) break;
        } catch (err) {
            lastError = err as Error;
            continue;
        }
    }

    if (!html || html.length < 100) {
        throw new Error(lastError?.message || 'Could not fetch website content. The site may be blocking requests.');
    }

    const emails = extractEmails(html);
    const phones = extractPhones(html);
    const companyName = extractCompanyName(html, url);
    const description = extractDescription(html);

    return { emails, phones, companyName, description };
}

function extractEmails(html: string): string[] {
    const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
    const emails = html.match(emailRegex) || [];
    const uniqueEmails = [...new Set(emails)];
    return uniqueEmails
        .filter(email => !email.match(/\.(png|jpg|jpeg|gif|svg|css|js|woff|ttf|ico|webp)$/i))
        .filter(email => !email.includes('example.com'))
        .filter(email => !email.startsWith('noreply'))
        .slice(0, 15);
}

function extractPhones(html: string): string[] {
    const phoneRegex = /(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/g;
    const phones = html.match(phoneRegex) || [];
    const uniquePhones = [...new Set(phones)];
    return uniquePhones
        .filter(phone => phone.replace(/\D/g, '').length >= 10)
        .slice(0, 15);
}

function extractCompanyName(html: string, url: string): string {
    const titleMatch = html.match(/<title[^>]*>([^<]+)<\/title>/i);
    if (titleMatch) {
        let title = titleMatch[1].trim();
        title = title.split(/[|\-–—]/)[0].trim();
        if (title.length > 2 && title.length < 100) return title;
    }

    const ogTitleMatch = html.match(/<meta[^>]*property=["']og:title["'][^>]*content=["']([^"']+)["']/i);
    if (ogTitleMatch) return ogTitleMatch[1].trim();

    const h1Match = html.match(/<h1[^>]*>([^<]+)<\/h1>/i);
    if (h1Match) return h1Match[1].trim();

    return extractDomainName(url);
}

function extractDescription(html: string): string {
    const metaDescMatch = html.match(
        /<meta[^>]*name=["']description["'][^>]*content=["']([^"']+)["']/i
    );
    if (metaDescMatch) return metaDescMatch[1].trim().substring(0, 300);

    const ogDescMatch = html.match(
        /<meta[^>]*property=["']og:description["'][^>]*content=["']([^"']+)["']/i
    );
    if (ogDescMatch) return ogDescMatch[1].trim().substring(0, 300);

    return '';
}

function extractDomainName(url: string): string {
    try {
        const urlObj = new URL(url);
        let domain = urlObj.hostname.replace('www.', '');
        domain = domain.split('.')[0];
        return domain.charAt(0).toUpperCase() + domain.slice(1);
    } catch {
        return 'Unknown Company';
    }
}

const categoryKeywords: Record<string, string[]> = {
    Technology: ['software', 'saas', 'app', 'tech', 'digital', 'cloud', 'api', 'platform', 'developer', 'code', 'programming', 'startup', 'ai', 'machine learning', 'data'],
    Healthcare: ['health', 'medical', 'hospital', 'clinic', 'doctor', 'patient', 'wellness', 'care', 'pharma', 'therapy', 'dental'],
    Finance: ['finance', 'bank', 'investment', 'trading', 'financial', 'loan', 'credit', 'insurance', 'wealth', 'fintech', 'crypto'],
    'E-commerce': ['shop', 'store', 'ecommerce', 'retail', 'product', 'cart', 'checkout', 'buy', 'sell', 'marketplace', 'fashion'],
    Marketing: ['marketing', 'advertising', 'seo', 'social media', 'campaign', 'brand', 'agency', 'creative', 'content', 'digital marketing'],
    'Real Estate': ['real estate', 'property', 'realtor', 'housing', 'apartment', 'rental', 'mortgage', 'home', 'land'],
    Education: ['education', 'school', 'university', 'learning', 'course', 'training', 'student', 'teach', 'academy', 'online learning'],
    Manufacturing: ['manufacturing', 'factory', 'production', 'industrial', 'machinery', 'equipment', 'supply chain'],
};

export function categorizeLead(html: string, categories: Category[]): string | null {
    const lowerHtml = html.toLowerCase();
    let bestMatch: string | null = null;
    let maxScore = 0;

    for (const category of categories) {
        const keywords = categoryKeywords[category.name] || [];
        let score = 0;

        for (const keyword of keywords) {
            const regex = new RegExp(keyword, 'gi');
            const matches = lowerHtml.match(regex);
            if (matches) score += matches.length;
        }

        if (score > maxScore) {
            maxScore = score;
            bestMatch = category.id;
        }
    }

    if (!bestMatch) {
        const otherCategory = categories.find(c => c.name === 'Other');
        return otherCategory ? otherCategory.id : null;
    }

    return bestMatch;
}
