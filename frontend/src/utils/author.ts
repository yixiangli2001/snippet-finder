/** Returns the display name for a snippet or collection owner.
 *  When owner_username is null (account was deleted), shows "Anonymous". */
export function displayOwner(username: string | null | undefined): string {
  return username ?? 'Anonymous';
}
