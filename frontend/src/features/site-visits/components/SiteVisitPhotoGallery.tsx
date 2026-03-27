import { useRef, useState } from 'react'
import { Image, Trash2, Upload, X, ChevronLeft, ChevronRight } from 'lucide-react'
import type { SiteVisit, SiteVisitPhoto } from '../types'
import { useDeletePhoto, useUploadPhoto } from '../hooks/use-site-visit-photos'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function photoUrl(filePath: string): string {
  return `${API_BASE}/${filePath}`
}

interface SiteVisitPhotoGalleryProps {
  visit: SiteVisit
}

export function SiteVisitPhotoGallery({ visit }: SiteVisitPhotoGalleryProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const uploadPhoto = useUploadPhoto(visit.id)
  const deletePhoto = useDeletePhoto(visit.id)
  const isEditable = visit.status === 'scheduled' || visit.status === 'in_progress'
  const photos = visit.photos

  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)

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

  const openLightbox = (index: number) => setLightboxIndex(index)
  const closeLightbox = () => setLightboxIndex(null)

  const showPrev = () =>
    setLightboxIndex((i) => (i !== null ? (i - 1 + photos.length) % photos.length : null))
  const showNext = () =>
    setLightboxIndex((i) => (i !== null ? (i + 1) % photos.length : null))

  const handleLightboxKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') closeLightbox()
    if (e.key === 'ArrowLeft') showPrev()
    if (e.key === 'ArrowRight') showNext()
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
          {photos.map((photo, index) => (
            <div
              key={photo.id}
              className="group relative aspect-square overflow-hidden rounded-lg bg-gray-100 cursor-pointer"
              onClick={() => openLightbox(index)}
            >
              <img
                src={photoUrl(photo.file_path)}
                alt={photo.caption ?? 'Foto de visita'}
                className="h-full w-full object-cover transition-transform duration-200 group-hover:scale-105"
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
                  onClick={(e) => {
                    e.stopPropagation()
                    deletePhoto.mutate(photo.id)
                  }}
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

      {/* Lightbox */}
      {lightboxIndex !== null && (
        <Lightbox
          photos={photos}
          index={lightboxIndex}
          onClose={closeLightbox}
          onPrev={showPrev}
          onNext={showNext}
          onKeyDown={handleLightboxKey}
        />
      )}
    </div>
  )
}

// ── Lightbox ──────────────────────────────────────────────────────────────────

interface LightboxProps {
  photos: SiteVisitPhoto[]
  index: number
  onClose: () => void
  onPrev: () => void
  onNext: () => void
  onKeyDown: (e: React.KeyboardEvent) => void
}

function Lightbox({ photos, index, onClose, onPrev, onNext, onKeyDown }: LightboxProps) {
  const photo = photos[index]

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/90"
      onClick={onClose}
      onKeyDown={onKeyDown}
      tabIndex={-1}
      // eslint-disable-next-line jsx-a11y/no-autofocus
      autoFocus
    >
      {/* Close */}
      <button
        onClick={onClose}
        className="absolute right-4 top-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
      >
        <X size={20} />
      </button>

      {/* Prev */}
      {photos.length > 1 && (
        <button
          onClick={(e) => { e.stopPropagation(); onPrev() }}
          className="absolute left-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
        >
          <ChevronLeft size={28} />
        </button>
      )}

      {/* Image */}
      <img
        src={photoUrl(photo.file_path)}
        alt={photo.caption ?? 'Foto de visita'}
        className="max-h-[90vh] max-w-[90vw] rounded-lg object-contain shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      />

      {/* Next */}
      {photos.length > 1 && (
        <button
          onClick={(e) => { e.stopPropagation(); onNext() }}
          className="absolute right-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
        >
          <ChevronRight size={28} />
        </button>
      )}

      {/* Caption + counter */}
      <div className="absolute bottom-4 left-0 right-0 text-center">
        {photo.caption && (
          <p className="mb-1 text-sm text-white/80">{photo.caption}</p>
        )}
        {photos.length > 1 && (
          <p className="text-xs text-white/50">{index + 1} / {photos.length}</p>
        )}
      </div>
    </div>
  )
}
