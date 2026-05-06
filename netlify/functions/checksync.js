const SUPABASE_URL = 'https://vtmzpjkjabuuyhsahhol.supabase.co';
const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ0bXpwamtqYWJ1dXloc2FoaG9sIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc2MTE4OTMsImV4cCI6MjA5MzE4Nzg5M30.EokwncNDVHsinnAqoHKNI9S0DW79t2N0hWpQhmMFlNQ';

exports.handler = async (event) => {
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Content-Type': 'application/json'
  };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers, body: '' };
  }

  const sbHeaders = {
    'apikey': SUPABASE_KEY,
    'Authorization': `Bearer ${SUPABASE_KEY}`,
    'Content-Type': 'application/json',
    'Prefer': 'resolution=merge-duplicates'
  };

  try {
    if (event.httpMethod === 'GET') {
      // Load checkbox state for a date
      const date = event.queryStringParameters?.date;
      if (!date) return { statusCode: 400, headers, body: JSON.stringify({error:'date required'}) };

      const res = await fetch(`${SUPABASE_URL}/rest/v1/daily_checklist?date=eq.${date}`, { headers: sbHeaders });
      const data = await res.json();
      return { statusCode: 200, headers, body: JSON.stringify(data) };
    }

    if (event.httpMethod === 'POST') {
      // Save checkbox state
      const body = JSON.parse(event.body || '{}');
      const res = await fetch(`${SUPABASE_URL}/rest/v1/daily_checklist`, {
        method: 'POST',
        headers: sbHeaders,
        body: JSON.stringify(body)
      });
      const data = await res.json();
      return { statusCode: 200, headers, body: JSON.stringify(data) };
    }

  } catch (e) {
    return { statusCode: 500, headers, body: JSON.stringify({error: e.message}) };
  }

  return { statusCode: 405, headers, body: JSON.stringify({error:'method not allowed'}) };
};
