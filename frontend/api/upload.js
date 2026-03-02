import { handleUpload } from '@vercel/blob/client';

export default async function handler(request, response) {
  const body = request.body;

  try {
    const jsonResponse = await handleUpload({
      body,
      request,
      onBeforeGenerateToken: async () => {
        return {
          allowedContentTypes: [
            'application/octet-stream',
            'image/x-exr',
            'video/quicktime',
            'video/mp4',
            'video/x-msvideo',
            'video/x-matroska',
            'video/webm',
            'image/png',
            'image/jpeg',
            'image/tiff',
            'image/bmp',
          ],
          addRandomSuffix: true,
        };
      },
      onUploadCompleted: async () => {},
    });

    return response.status(200).json(jsonResponse);
  } catch (error) {
    return response.status(400).json({ error: error.message });
  }
}
