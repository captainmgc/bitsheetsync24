# 🚀 ADIM C - Quick Reference

## 📁 Frontend File Structure

```
frontend/
├── hooks/
│   └── useSheetSync.ts (520 lines)
│       ├── State: isLoading, error, userToken, syncConfigs, syncLogs
│       ├── OAuth: startOAuth, completeOAuth, revokeAccess
│       ├── Config: createSyncConfig, getSyncConfig, deleteSyncConfig
│       ├── Mapping: updateFieldMapping
│       └── History: loadSyncHistory, retryFailedSyncs, getSyncStatus
│
├── app/sheet-sync/
│   ├── page.tsx (300 lines - Main page with tabs)
│   ├── oauth/callback/page.tsx (150 lines - OAuth handler)
│   └── components/
│       ├── GoogleSheetConnect.tsx (100 lines - OAuth button)
│       ├── SheetSelector.tsx (350 lines - Config CRUD)
│       ├── FieldMappingDisplay.tsx (250 lines - Field editor)
│       ├── ColorSchemePicker.tsx (320 lines - Color customization)
│       └── SyncHistory.tsx (400 lines - Logs & history)
```

---

## 🎯 Component Quick Guide

### `useSheetSync` Hook
```typescript
import { useSheetSync } from '@/hooks/useSheetSync';

const {
  // State
  isLoading, error, userToken, syncConfigs, currentConfig, syncLogs,
  
  // OAuth
  startOAuth, completeOAuth, revokeAccess,
  
  // Config
  createSyncConfig, getSyncConfig, deleteSyncConfig, loadSyncConfigs,
  
  // Mapping
  updateFieldMapping,
  
  // History
  loadSyncHistory, retryFailedSyncs, getSyncStatus
} = useSheetSync();
```

### Page Structure
```
/sheet-sync/
├── No Auth → Show GoogleSheetConnect
├── Authenticated
│   ├── Tab 1: SheetSelector (Create/List configs)
│   ├── Tab 2: FieldMappingDisplay (Edit mappings)
│   ├── Tab 3: ColorSchemePicker (Customize colors)
│   ├── Tab 4: SyncHistory (View logs)
│   └── Tab 5: Settings (Future)
```

---

## 🔄 Data Flow

```
User → Frontend Hook → Backend API → Database
 ↓           ↓              ↓            ↓
Click    Call API      /api/v1/   PostgreSQL
Button   Endpoint      sheet-sync   Tables
  ↓           ↓              ↓            ↓
Update   Response    ← Success →   Update
State    Handler       Status      Record
```

---

## 📊 API Endpoints Used

| Method | Endpoint | Hook Method |
|--------|----------|-------------|
| POST | /oauth/start | startOAuth() |
| GET | /oauth/callback | completeOAuth() |
| POST | /config | createSyncConfig() |
| GET | /config/{id} | getSyncConfig() |
| DELETE | /config/{id} | deleteSyncConfig() |
| POST | /field-mapping/{id} | updateFieldMapping() |
| GET | /logs/{config_id} | loadSyncHistory() |
| GET | /status/{log_id} | getSyncStatus() |
| POST | /retry/{config_id} | retryFailedSyncs() |

---

## 🎨 Component Features

### GoogleSheetConnect ✨
- OAuth connect button
- Permissions explanation
- Privacy notice
- Error handling

### SheetSelector 📋
- Create new config form
- Config list display
- Status badges
- Delete button
- Entity type selector

### FieldMappingDisplay 🔗
- Auto-detected mappings table
- Data type indicators
- Bitrix field dropdown
- Updatable checkbox
- Inline edit/save

### ColorSchemePicker 🎨
- 6 preset schemes
- Custom color picker
- Hex input fields
- Live table preview
- Poppins font (locked)

### SyncHistory 📊
- Operation logs table
- Status filters
- Auto-refresh toggle
- Retry failed button
- Details expansion
- Statistics summary

---

## 🌟 Key Interfaces

```typescript
UserSheetsToken {
  user_id: string
  user_email: string
  is_active: boolean
  last_used_at: string
}

SyncConfig {
  id: number
  sheet_id: string
  sheet_name: string
  gid: string
  entity_type: 'contacts' | 'deals' | 'companies' | 'tasks'
  webhook_url: string
  enabled: boolean
  color_scheme: { primary?: string; secondary?: string; accent?: string }
  created_at: string
  last_sync_at?: string
  field_mappings: FieldMapping[]
}

FieldMapping {
  id: number
  sheet_column_index: number
  sheet_column_name: string
  bitrix_field: string
  data_type: 'string' | 'number' | 'date' | 'boolean'
  is_updatable: boolean
}

SyncLog {
  id: number
  entity_id: string
  row_id: number
  status: 'pending' | 'syncing' | 'completed' | 'failed' | 'retrying'
  changes: Record<string, { old: unknown; new: unknown }>
  error?: string
  created_at: string
  updated_at?: string
}
```

---

## 🎯 Common Tasks

### Add New Tab
```typescript
// In page.tsx
{activeTab === 'new_tab' && (
  <NewComponent config={currentConfig} />
)}

// Add button to tab navigation
{ id: 'new_tab' as Tab, label: '📌 New Tab', icon: '📌' }
```

### Add New Component
```typescript
// Create component file
export default function NewComponent({ config }) {
  return <div>Component content</div>
}

// Import in page.tsx
import NewComponent from './components/NewComponent'
```

### Call API
```typescript
const { createSyncConfig, isLoading, error } = useSheetSync();

const handleCreate = async () => {
  const config = await createSyncConfig({ ... });
  if (config) {
    // Success
  }
}
```

### Add Status Filter
```typescript
const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | ...>('all');

useEffect(() => {
  onLoadHistory(configId, statusFilter === 'all' ? undefined : statusFilter);
}, [statusFilter]);
```

---

## 🎯 Hook Usage Pattern

```typescript
// 1. Import hook
import { useSheetSync } from '@/hooks/useSheetSync';

// 2. Destructure needed methods
const { 
  createSyncConfig, 
  isLoading, 
  error 
} = useSheetSync();

// 3. Use in handler
const handleCreate = async (data) => {
  try {
    const result = await createSyncConfig(data);
    if (result) {
      // Success
    }
  } catch (err) {
    // Error handled by hook
  }
}

// 4. Render with state
return (
  <>
    {isLoading && <Spinner />}
    {error && <ErrorBanner message={error} />}
    <button onClick={handleCreate}>Create</button>
  </>
);
```

---

## 🔐 Auth Flow

```
1. User not logged in
   ↓
2. Redirect to /auth/signin (NextAuth)
   ↓
3. User logs in
   ↓
4. Session created
   ↓
5. Redirect to /sheet-sync
   ↓
6. Show "Connect Google Sheets" button
   ↓
7. User clicks button
   ↓
8. startOAuth() called
   ↓
9. Redirect to Google OAuth
   ↓
10. User authorizes
    ↓
11. Return to /sheet-sync/oauth/callback
    ↓
12. completeOAuth() exchanges code for tokens
    ↓
13. Tokens saved to backend
    ↓
14. Redirect to /sheet-sync/config
    ↓
15. Show "New Configuration" form
```

---

## 🎨 Color Scheme Structure

```typescript
color_scheme: {
  primary: '#1f2937',     // Header/main background
  secondary: '#374151',   // Footer background
  accent: '#3b82f6'       // Status badges
}

PRESET_SCHEMES:
- Default: Gray/Blue
- Ocean: Cyan/Blue
- Forest: Green
- Sunset: Orange
- Purple: Purple
- Pink: Pink
```

---

## 📱 Responsive Breakpoints

```
Mobile    (< 640px):  1 column
Tablet    (640-1024): 2 columns
Desktop   (> 1024px): 3+ columns

Tailwind classes:
sm:px-6    - Small padding
md:grid-cols-3 - Medium: 3 columns
lg:px-8    - Large padding
```

---

## 🧪 Testing Quick Start

```typescript
// Test hook
describe('useSheetSync', () => {
  it('should load sync configs', async () => {
    const { result } = renderHook(() => useSheetSync());
    // Test implementation
  });
});

// Test component
describe('GoogleSheetConnect', () => {
  it('should render connect button', () => {
    render(<GoogleSheetConnect />);
    expect(screen.getByText('Connect with Google')).toBeInTheDocument();
  });
});
```

---

## 🔗 Important Links

| Resource | Location |
|----------|----------|
| Backend API | `http://localhost:8000/api/v1/sheet-sync` |
| API Docs | `http://localhost:8000/docs` |
| Frontend | `http://localhost:3000/sheet-sync` |
| Callback | `http://localhost:3000/sheet-sync/oauth/callback` |

---

## ⚡ Performance Tips

1. **Hook memoization**: useCallback for handlers
2. **Lazy loading**: Code splitting for components
3. **Image optimization**: next/image for images
4. **API caching**: Use React Query (optional)
5. **Bundle size**: Monitor with webpack analyzer

---

## 🚀 Deployment

```bash
# Build
npm run build

# Run production
npm run start

# Or deploy to Vercel
vercel deploy
```

---

## 📝 Common Errors & Solutions

| Error | Solution |
|-------|----------|
| "Cannot find module" | Check import path and file exists |
| "Type error" | Add type annotations or interfaces |
| "API 404" | Verify backend endpoint URL |
| "CORS error" | Check backend CORS configuration |
| "Session expired" | Re-authenticate with Google |

---

## 🎓 Best Practices

✅ **Do**:
- Use hook for state management
- Handle loading/error states
- Show user feedback
- Validate inputs
- Log important events

❌ **Don't**:
- Make API calls in render
- Store tokens in localStorage
- Skip error handling
- Block UI during requests
- Hardcode API URLs

---

**ADIM C: Frontend Implementation Complete! ✅**

All components created, integrated, and ready for testing.

Next: Testing & Integration → Documentation
