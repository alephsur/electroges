import { useRef } from 'react'
import { Image, Trash2, Upload } from 'lucide-react'
import type { SiteVisit } from '../types'
import { useDeletePhoto, useUploadPhoto } from '../hooks/use-site-visit-photos'

interface SiteVisitPhotoGalleryProps {
  visit: SiteVisit
}

export function SiteVisitPhotoGallery({ visit }: SiteVisitPhotoGalleryProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const uploadPhoto = useUploadPhoto(visit.id)
  const deletePhoto = useDeletePhoto(visit.id)
  const isEditable = visit.status === 'scheduled' || visit.status === 'in_progress'
  const photos = visit.photos

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files?.length) return
    Array.from(files).forEach((file) => uploadPhoto.mutate({ file }))
    e.target.value = ''
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    if (!isEditable) return
    Array.from(e.dataTransfer.files)
      .filter((f) => f.type.startsWith('image/'))
      .forEach((file) => uploadPhoto.mutate({ file }))
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500">
          {photos.length} foto{photos.length !== 1 ? 's' : ''}
        </span>
        {isEditable && (
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadPhoto.isPending}
            className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700 disabled:opacity-50"
          >
            <Upload size={14} />
            {uploadPhoto.isPending ? 'Subiendo...' : 'Añadir foto'}
          </button>
        )}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        multiple
        className="hidden"
        onChange={handleFileChange}
      />

      {photos.length === 0 ? (
        <div
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          onClick={() => isEditable && fileInputRef.current?.click()}
          className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-200 py-12 text-center ${
            isEditable ? 'cursor-pointer hover:border-blue-300 hover:bg-blue-50' : ''
          }`}
        >
          <Image size={36} className="mb-2 text-gray-300" />
          <p className="text-sm text-gray-400">
            {isEditable
              ? 'Arrastra imágenes aquí o haz clic para subir'
              : 'Sin fotos adjuntas'}
          </p>
        </div>
      ) : (
        <div
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          className="grid grid-cols-3 gap-3"
        >
          {photos.map((photo) => (
            <div
              key={photo.id}
              className="group relative aspect-square overflow-hidden rounded-lg bg-gray-100"
            >
              <img
                src={photo.file_path}
                alt={photo.caption ?? 'Foto de visita'}
                className="h-full w-full object-cover"
                onError={(e) => {
                  const el = e.target as HTMLImageElement
                  el.style.display = 'none'
                }}
              />
              {photo.caption && (
                <div className="absolute bottom-0 left-0 right-0 bg-black/50 px-2 py-1">
                  <p className="truncate text-xs text-white">{photo.caption}</p>
                </div>
              )}
              {isEditable && (
                <button
                  onClick={() => deletePhoto.mutate(photo.id)}
                  disabled={deletePhoto.isPending}
                  className="absolute right-1 top-1 hidden rounded-full bg-red-600 p-1 text-white group-hover:block disabled:opacity-50"
                >
                  <Trash2 size={10} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
