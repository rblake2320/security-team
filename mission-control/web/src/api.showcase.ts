import type { MissionState } from './api-types'
import { useSnapshotFeed } from './snapshot'

const CONTROL_DISABLED_MESSAGE = 'Control actions are unavailable in the public read-only showcase.'

const runGate: MissionState['runGate'] = async () => { throw new Error(CONTROL_DISABLED_MESSAGE) }
const decideTask: MissionState['decideTask'] = async () => { throw new Error(CONTROL_DISABLED_MESSAGE) }
const decideAsset: MissionState['decideAsset'] = async () => { throw new Error(CONTROL_DISABLED_MESSAGE) }
const decideViolation: MissionState['decideViolation'] = async () => { throw new Error(CONTROL_DISABLED_MESSAGE) }
const updateShadowPolicy: MissionState['updateShadowPolicy'] = async () => { throw new Error(CONTROL_DISABLED_MESSAGE) }
const updateRetention: MissionState['updateRetention'] = async () => { throw new Error(CONTROL_DISABLED_MESSAGE) }
const updateSafety: MissionState['updateSafety'] = async () => { throw new Error(CONTROL_DISABLED_MESSAGE) }
const provisionConnector: MissionState['provisionConnector'] = async () => { throw new Error(CONTROL_DISABLED_MESSAGE) }
const createEngagement: MissionState['createEngagement'] = async () => { throw new Error(CONTROL_DISABLED_MESSAGE) }
const uploadEngagementAssets: MissionState['uploadEngagementAssets'] = async () => { throw new Error(CONTROL_DISABLED_MESSAGE) }
const launchEngagement: MissionState['launchEngagement'] = async () => { throw new Error(CONTROL_DISABLED_MESSAGE) }
const analyzeEngagementAsset: MissionState['analyzeEngagementAsset'] = async () => { throw new Error(CONTROL_DISABLED_MESSAGE) }
const compareEngagementRuns: MissionState['compareEngagementRuns'] = async () => { throw new Error(CONTROL_DISABLED_MESSAGE) }
const engagementExportUrl: MissionState['engagementExportUrl'] = () => null
const evidenceDownloadUrl: MissionState['evidenceDownloadUrl'] = () => null

export function useMissionControl(): MissionState {
  const feed = useSnapshotFeed()
  const snapshot = feed.snapshot
    ? {
        ...feed.snapshot,
        deployment: {
          ...feed.snapshot.deployment,
          mode: 'demo' as const,
          controlsEnabled: false,
          streamingEnabled: false,
          authentication: 'public-read-only' as const,
        },
        platform: undefined,
      }
    : null
  return {
    ...feed,
    snapshot,
    runGate,
    decideTask,
    decideAsset,
    decideViolation,
    updateShadowPolicy,
    updateRetention,
    updateSafety,
    provisionConnector,
    createEngagement,
    uploadEngagementAssets,
    launchEngagement,
    analyzeEngagementAsset,
    compareEngagementRuns,
    engagementExportUrl,
    evidenceDownloadUrl,
  }
}
