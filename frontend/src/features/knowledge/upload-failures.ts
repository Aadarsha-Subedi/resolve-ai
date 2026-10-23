/** Why a file could not be read, by the backend's error code. */
const FAILURES: Record<string, string> = {
  document_corrupt: 'The file looks damaged or is protected with a password.',
  document_empty: 'No text was found in the file.',
  document_too_large: 'The document has too many pages to read.',
  document_timeout: 'Reading the file took too long.',
  document_unsupported: 'This file type cannot be read.',
}
const FAILURE_DEFAULT = 'Something went wrong while reading the file.'

export function failureMessage(code: string | null): string {
  return (code && FAILURES[code]) || FAILURE_DEFAULT
}

