exports.handler = async (event) => {
  const SUPABASE_URL = 'https://vtmzpjkjabuuyhsahhol.supabase.co';
  const SUPABASE_KEY = process.env.SUPABASE_KEY;

  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Content-Type': 'application/json'
  };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers, body: '' };
  }

  if (!SUPABASE_KEY) {
    return { statusCode: 500, headers, body: JSON.stringify({error: 'Missing SUPABASE_KEY'}) };
  }

  const sbHeaders = {
    'apikey': SUPABASE_KEY,
    'Authorization': `Bearer ${SUPABASE_KEY}`,
    'Content-Type': 'application/json',
    'Prefer': 'resolution=merge-duplicates'
  };

  try {
    if (event.httpMethod === 'GET') {
      const date = event.queryStringParameters?.date;
      if (!date) return { statusCode: 400, headers, body: JSON.stringify({error:'date required'}) };
      const res = await fetch(
        `${SUPABASE_URL}/rest/v1/daily_checklist?date=eq.${date}&select=item_id,checked`,
        { headers: sbHeaders }
      );
      const data = await res.json();
      return { statusCode: 200, headers, body: JSON.stringify(data) };
    }

    if (event.httpMethod === 'POST') {
      const body = JSON.parse(event.body || '{}');
      // Use upsert — merge on date+item_id so we never overwrite other items
      const res = await fetch(`${SUPABASE_URL}/rest/v1/daily_checklist`, {
        method: 'POST',
        headers: {
          ...sbHeaders,
          'Prefer': 'resolution=merge-duplicates,return=minimal'
        },
        body: JSON.stringify(body)
      });
      return { statusCode: 200, headers, body: JSON.stringify({ok: true}) };
    }

  } catch (e) {
    return { statusCode: 500, headers, body: JSON.stringify({error: e.message}) };
  }

  return { statusCode: 405, headers, body: JSON.stringify({error:'method not allowed'}) };
};
