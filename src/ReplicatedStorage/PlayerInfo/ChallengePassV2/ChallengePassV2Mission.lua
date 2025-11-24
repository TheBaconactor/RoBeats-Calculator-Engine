-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:14 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v2 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_4 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_5 = require(game.ReplicatedStorage.Shared.Bit)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_7 = {
    ["DailyMissionType"] = {
        ["Complete1DailyMission"] = 1,
        ["Complete3DailyMission"] = 2,
        ["Complete6DailyMission"] = 3,
        ["VoteDJ"] = 4,
        ["QueueDJ"] = 5,
        ["SpeakWebNPC"] = 6,
        ["BuySongShop"] = 7,
        ["CheerSpectate"] = 8,
        ["Play3PlayerMatch"] = 9,
        ["PlayEventSong"] = 10,
        ["UpgradeGear"] = 11,
        ["PostTeamMessageBoard"] = 12,
        ["LikeOrPostWebNPC"] = 13,
        ["SendPetTraining"] = 14
    }
}
local v_u_8 = v2:new({
    [v_u_7.DailyMissionType.Complete1DailyMission] = "Complete 1 daily song mission",
    [v_u_7.DailyMissionType.Complete3DailyMission] = "Complete 3 daily song missions",
    [v_u_7.DailyMissionType.Complete6DailyMission] = "Complete 6 daily song missions",
    [v_u_7.DailyMissionType.VoteDJ] = "Up-vote a DJ song",
    [v_u_7.DailyMissionType.QueueDJ] = "Queue a DJ song",
    [v_u_7.DailyMissionType.SpeakWebNPC] = "Find a player NPC with rewards",
    [v_u_7.DailyMissionType.BuySongShop] = "Buy a song from the shop",
    [v_u_7.DailyMissionType.CheerSpectate] = "Cheer while spectating",
    [v_u_7.DailyMissionType.Play3PlayerMatch] = "Complete a 3 (or more) player match",
    [v_u_7.DailyMissionType.PlayEventSong] = "Play an event song",
    [v_u_7.DailyMissionType.UpgradeGear] = "Upgrade your gear",
    [v_u_7.DailyMissionType.PostTeamMessageBoard] = "Post on team or leaderboard message board",
    [v_u_7.DailyMissionType.LikeOrPostWebNPC] = "Like or respond to another player\'s NPC",
    [v_u_7.DailyMissionType.SendPetTraining] = "Send a mini training assignment"
})
local v_u_9 = v2:new()
local v_u_10 = v2:new()
for _, v11 in pairs(v_u_7.DailyMissionType) do
    v_u_10:add(v11, 20)
    v_u_9:add_set(v11)
end;
v_u_10:add(v_u_7.DailyMissionType.Complete3DailyMission, 40)
v_u_10:add(v_u_7.DailyMissionType.Complete6DailyMission, 80)
v_u_10:add(v_u_7.DailyMissionType.Play3PlayerMatch, 50)
v_u_10:add(v_u_7.DailyMissionType.UpgradeGear, 50)
v_u_7.get_daily_mission_name = function(_, p12) --[[ Name: get_daily_mission_name ]] --[[ Line: 61 ]]
    --[[ Upvalues: (copy 1): v_u_8 ]]
    return v_u_8:get(p12);
end;
v_u_7.get_daily_mission_point_amount = function(_, p13) --[[ Name: get_daily_mission_point_amount ]] --[[ Line: 62 ]]
    --[[ Upvalues: (copy 1): v_u_10 ]]
    return v_u_10:get(p13);
end;
v_u_7.get_daily_point_cap = function(_) --[[ Name: get_daily_point_cap ]] --[[ Line: 63 ]]
    return 150;
end;
v_u_7.get_daily_mission_type_set = function(_) --[[ Name: get_daily_mission_type_set ]] --[[ Line: 64 ]]
    --[[ Upvalues: (copy 1): v_u_9 ]]
    return v_u_9;
end;
v_u_7.WeeklyMissionType = {
    ["CraftSong"] = 1,
    ["EnterWeeklyLeaderboard"] = 2,
    ["RollNoteMachine"] = 3,
    ["RollStarMachine"] = 4,
    ["CompeteInEventLeaderboard"] = 5,
    ["CompleteWeeklyMission"] = 6,
    ["CompleteChallengeMission"] = 7
}
local v_u_14 = v2:new({
    [v_u_7.WeeklyMissionType.CraftSong] = "Craft a song",
    [v_u_7.WeeklyMissionType.EnterWeeklyLeaderboard] = "Enter a weekly leaderboard",
    [v_u_7.WeeklyMissionType.RollNoteMachine] = "Roll the note machine",
    [v_u_7.WeeklyMissionType.RollStarMachine] = "Roll the song machine",
    [v_u_7.WeeklyMissionType.CompeteInEventLeaderboard] = "Enter and claim rewards from an event leaderboard",
    [v_u_7.WeeklyMissionType.CompleteWeeklyMission] = "Complete a weekly song mission",
    [v_u_7.WeeklyMissionType.CompleteChallengeMission] = "Complete a daily song no-miss challenge mission"
})
local v_u_15 = v2:new()
local v_u_16 = v2:new()
for _, v17 in pairs(v_u_7.WeeklyMissionType) do
    v_u_15:add(v17, 150)
    v_u_16:add_set(v17)
end;
v_u_7.get_weekly_mission_name = function(_, p18) --[[ Name: get_weekly_mission_name ]] --[[ Line: 93 ]]
    --[[ Upvalues: (copy 1): v_u_14 ]]
    return v_u_14:get(p18);
end;
v_u_7.get_weekly_mission_point_amount = function(_, p19) --[[ Name: get_weekly_mission_point_amount ]] --[[ Line: 94 ]]
    --[[ Upvalues: (copy 1): v_u_15 ]]
    return v_u_15:get(p19);
end;
v_u_7.get_weekly_point_cap = function(_) --[[ Name: get_weekly_point_cap ]] --[[ Line: 95 ]]
    return 750;
end;
v_u_7.get_weekly_mission_type_set = function(_) --[[ Name: get_weekly_mission_type_set ]] --[[ Line: 96 ]]
    --[[ Upvalues: (copy 1): v_u_16 ]]
    return v_u_16;
end;
v_u_7.playerblob_get_points_total = function(_, p20) --[[ Name: playerblob_get_points_total ]] --[[ Line: 109 ]]
    return p20.CPV2Points;
end;
v_u_7.playerblob_get_daily_mission_flags = function(_, p21) --[[ Name: playerblob_get_daily_mission_flags ]] --[[ Line: 110 ]]
    return p21.CPV2DayFlags;
end;
v_u_7.playerblob_get_weekly_mission_flags = function(_, p22) --[[ Name: playerblob_get_weekly_mission_flags ]] --[[ Line: 111 ]]
    return p22.CPV2WeekFlags;
end;
v_u_7.playerblob_has_challengepass_vip_unlocked_for_dayid_monthid = function(_, p23, p24, p25) --[[ Name: playerblob_has_challengepass_vip_unlocked_for_dayid_monthid ]] --[[ Line: 112 ]]
    --[[ Upvalues: (copy 1): v_u_6 ]]
    return v_u_6:playerblob_has_vip_for_current_day(p23, p24) == true and true or p23.CPV2MonthUpgradeToVIP == true and p23.CPV2MonthID == p25;
end;
v_u_7.playerblob_get_standard_claimed_tier = function(_, p26) --[[ Name: playerblob_get_standard_claimed_tier ]] --[[ Line: 121 ]]
    return p26.CPV2StandardClaimedTier;
end;
v_u_7.playerblob_set_standard_claimed_tier = function(_, p27, p28) --[[ Name: playerblob_set_standard_claimed_tier ]] --[[ Line: 122 ]]
    --[[ Upvalues: (copy 1): v_u_4 ]]
    v_u_4:is_int(p28)
    p27.CPV2StandardClaimedTier = p28
end;
v_u_7.playerblob_get_vip_claimed_tier = function(_, p29) --[[ Name: playerblob_get_vip_claimed_tier ]] --[[ Line: 126 ]]
    return p29.CPV2VIPClaimedTier;
end;
v_u_7.playerblob_set_vip_claimed_tier = function(_, p30, p31) --[[ Name: playerblob_set_vip_claimed_tier ]] --[[ Line: 127 ]]
    --[[ Upvalues: (copy 1): v_u_4 ]]
    v_u_4:is_int(p31)
    p30.CPV2VIPClaimedTier = p31
end;
local function _(p32, p33) --[[ Name: flag_is_set ]] --[[ Line: 132 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_5 ]]
    local v34 = v_u_4
    local v35
    if p33 > 0 then
        v35 = p33 <= 32
    else
        v35 = false
    end;
    v34:is_true(v35)
    return v_u_5.And(p32, v_u_5.LShift(1, p33 - 1)) ~= 0;
end;
local function _(p36, p37) --[[ Name: set_flag ]] --[[ Line: 137 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_5 ]]
    local v38 = v_u_4
    local v39
    if p37 > 0 then
        v39 = p37 <= 32
    else
        v39 = false
    end;
    v38:is_true(v39)
    return v_u_5.Or(p36, v_u_5.LShift(1, p37 - 1));
end;
v_u_7.playerblob_daily_mission_flag_set = function(_, p40, p41) --[[ Name: playerblob_daily_mission_flag_set ]] --[[ Line: 142 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_4, (copy 3): v_u_5 ]]
    local v42 = v_u_7:playerblob_get_daily_mission_flags(p40)
    local v43 = v_u_4
    local v44
    if p41 > 0 then
        v44 = p41 <= 32
    else
        v44 = false
    end;
    v43:is_true(v44)
    return v_u_5.And(v42, v_u_5.LShift(1, p41 - 1)) ~= 0;
end;
v_u_7.playerblob_weekly_mission_flag_set = function(_, p45, p46) --[[ Name: playerblob_weekly_mission_flag_set ]] --[[ Line: 143 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_4, (copy 3): v_u_5 ]]
    local v47 = v_u_7:playerblob_get_weekly_mission_flags(p45)
    local v48 = v_u_4
    local v49
    if p46 > 0 then
        v49 = p46 <= 32
    else
        v49 = false
    end;
    v48:is_true(v49)
    return v_u_5.And(v47, v_u_5.LShift(1, p46 - 1)) ~= 0;
end;
v_u_7.playerblob_get_daily_mission_points = function(_, p50) --[[ Name: playerblob_get_daily_mission_points ]] --[[ Line: 145 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_10, (copy 3): v_u_4, (copy 4): v_u_5 ]]
    local v51 = v_u_7:playerblob_get_daily_mission_flags(p50)
    local v52 = 0
    for v53, v54 in v_u_10:key_itr() do
        local v55 = v_u_4
        local v56
        if v53 > 0 then
            v56 = v53 <= 32
        else
            v56 = false
        end;
        v55:is_true(v56)
        if v_u_5.And(v51, v_u_5.LShift(1, v53 - 1)) ~= 0 == true then
            v52 = v52 + v54
        end;
    end;
    return math.min(v52, v_u_7:get_daily_point_cap());
end;
v_u_7.playerblob_get_weekly_mission_points = function(_, p57) --[[ Name: playerblob_get_weekly_mission_points ]] --[[ Line: 156 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_15, (copy 3): v_u_4, (copy 4): v_u_5 ]]
    local v58 = v_u_7:playerblob_get_weekly_mission_flags(p57)
    local v59 = 0
    for v60, v61 in v_u_15:key_itr() do
        local v62 = v_u_4
        local v63
        if v60 > 0 then
            v63 = v60 <= 32
        else
            v63 = false
        end;
        v62:is_true(v63)
        if v_u_5.And(v58, v_u_5.LShift(1, v60 - 1)) ~= 0 == true then
            v59 = v59 + v61
        end;
    end;
    return math.min(v59, v_u_7:get_weekly_point_cap());
end;
v_u_7.playerblob_has_any_claimable_rewards_for_day_month = function(_, p64, p65, p66, p67) --[[ Name: playerblob_has_any_claimable_rewards_for_day_month ]] --[[ Line: 167 ]]
    --[[ Upvalues: (copy 1): v_u_7 ]]
    local v68 = v_u_7:playerblob_get_points_total(p64)
    local v69 = v_u_7:playerblob_has_challengepass_vip_unlocked_for_dayid_monthid(p64, p66, p67)
    local v70 = v_u_7:playerblob_get_standard_claimed_tier(p64)
    local v71 = v_u_7:playerblob_get_vip_claimed_tier(p64)
    local v72 = 0
    for v73 = 1, p65:count() do
        if p65:get(v73):get_points() > v68 then
            break;
        end;
        if v69 and v71 < v73 then
            v72 = v72 + 1
        end;
        if v70 < v73 then
            v72 = v72 + 1
        end;
    end;
    return v72 > 0, v72;
end;
local function _(p74, p75) --[[ Name: playerblob_validate_monthid ]] --[[ Line: 192 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3 ]]
    if p74.CPV2MonthID ~= p75 then
        p74.CPV2MonthID = p75
        p74.CPV2Points = 0
        p74.CPV2MonthUpgradeToVIP = false
        p74.CPV2StandardClaimedTier = 0
        p74.CPV2VIPClaimedTier = 0
        if v_u_1:is_dev_build() then
            v_u_3:puts("ChallengePassV2Mission:playerblob_validate_monthid reset monthid(%d)", p75)
        end;
    end;
end;
local function _(p76, p77) --[[ Name: playerblob_validate_weekid ]] --[[ Line: 205 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3 ]]
    if p76.CPV2WeekID ~= p77 then
        p76.CPV2WeekID = p77
        p76.CPV2WeekFlags = 0
        if v_u_1:is_dev_build() then
            v_u_3:puts("ChallengePassV2Mission:weekly_mission_type_playerblob_claim_weekid reset weekid(%d)", p77)
        end;
    end;
end;
local function _(p78, p79) --[[ Name: playerblob_validate_dayid ]] --[[ Line: 215 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3 ]]
    if p78.CPV2DayID ~= p79 then
        p78.CPV2DayID = p79
        p78.CPV2DayFlags = 0
        if v_u_1:is_dev_build() then
            v_u_3:puts("ChallengePassV2Mission:playerblob_validate_dayid reset dayid(%d)", p79)
        end;
    end;
end;
v_u_7.validate_playerblob_to_current_day_week_month_id = function(_, p80, p81, p82, p83) --[[ Name: validate_playerblob_to_current_day_week_month_id ]] --[[ Line: 225 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3 ]]
    if p80.CPV2MonthID ~= p83 then
        p80.CPV2MonthID = p83
        p80.CPV2Points = 0
        p80.CPV2MonthUpgradeToVIP = false
        p80.CPV2StandardClaimedTier = 0
        p80.CPV2VIPClaimedTier = 0
        if v_u_1:is_dev_build() then
            v_u_3:puts("ChallengePassV2Mission:playerblob_validate_monthid reset monthid(%d)", p83)
        end;
    end;
    if p80.CPV2WeekID ~= p82 then
        p80.CPV2WeekID = p82
        p80.CPV2WeekFlags = 0
        if v_u_1:is_dev_build() then
            v_u_3:puts("ChallengePassV2Mission:weekly_mission_type_playerblob_claim_weekid reset weekid(%d)", p82)
        end;
    end;
    if p80.CPV2DayID ~= p81 then
        p80.CPV2DayID = p81
        p80.CPV2DayFlags = 0
        if v_u_1:is_dev_build() then
            v_u_3:puts("ChallengePassV2Mission:playerblob_validate_dayid reset dayid(%d)", p81)
        end;
    end;
end;
v_u_7.can_claim_daily_mission_type_playerblob_dayid_monthid = function(_, p84, p85, p86, p87) --[[ Name: can_claim_daily_mission_type_playerblob_dayid_monthid ]] --[[ Line: 231 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_4, (copy 4): v_u_7, (copy 5): v_u_5 ]]
    if p85.CPV2MonthID ~= p87 then
        p85.CPV2MonthID = p87
        p85.CPV2Points = 0
        p85.CPV2MonthUpgradeToVIP = false
        p85.CPV2StandardClaimedTier = 0
        p85.CPV2VIPClaimedTier = 0
        if v_u_1:is_dev_build() then
            v_u_3:puts("ChallengePassV2Mission:playerblob_validate_monthid reset monthid(%d)", p87)
        end;
    end;
    if p85.CPV2DayID ~= p86 then
        p85.CPV2DayID = p86
        p85.CPV2DayFlags = 0
        if v_u_1:is_dev_build() then
            v_u_3:puts("ChallengePassV2Mission:playerblob_validate_dayid reset dayid(%d)", p86)
        end;
    end;
    if v_u_4:test_enum_member(p84, v_u_7.DailyMissionType) ~= true then
        v_u_3:warnf("ChallengePassV2Mission:can_claim_daily_mission_type_playerblob_dayid_monthid is not enum member(%s)", (tostring(p84)))
        return false;
    end;
    local v88 = v_u_7:playerblob_get_daily_mission_flags(p85)
    local v89 = v_u_4
    local v90
    if p84 > 0 then
        v90 = p84 <= 32
    else
        v90 = false
    end;
    v89:is_true(v90)
    return v_u_5.And(v88, v_u_5.LShift(1, p84 - 1)) ~= 0 ~= true;
end;
v_u_7.daily_mission_type_playerblob_claim_dayid_monthid = function(_, p91, p92, p93, p94) --[[ Name: daily_mission_type_playerblob_claim_dayid_monthid ]] --[[ Line: 244 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_4, (copy 4): v_u_7, (copy 5): v_u_5, (copy 6): v_u_10 ]]
    if p92.CPV2MonthID ~= p94 then
        p92.CPV2MonthID = p94
        p92.CPV2Points = 0
        p92.CPV2MonthUpgradeToVIP = false
        p92.CPV2StandardClaimedTier = 0
        p92.CPV2VIPClaimedTier = 0
        if v_u_1:is_dev_build() then
            v_u_3:puts("ChallengePassV2Mission:playerblob_validate_monthid reset monthid(%d)", p94)
        end;
    end;
    if p92.CPV2DayID ~= p93 then
        p92.CPV2DayID = p93
        p92.CPV2DayFlags = 0
        if v_u_1:is_dev_build() then
            v_u_3:puts("ChallengePassV2Mission:playerblob_validate_dayid reset dayid(%d)", p93)
        end;
    end;
    if p92.CPV2DayID ~= p93 then
        p92.CPV2DayID = p93
        p92.CPV2DayFlags = 0
        if v_u_1:is_dev_build() then
            v_u_3:warnf("ChallengePassV2Mission:daily_mission_type_playerblob_claim_dayid reset dayid(%d)", p93)
        end;
    end;
    if v_u_4:test_enum_member(p91, v_u_7.DailyMissionType) ~= true then
        v_u_3:warnf("ChallengePassV2Mission:daily_mission_type_playerblob_claim is not enum member(%s)", (tostring(p91)))
        return 0;
    end;
    local v95 = v_u_7:playerblob_get_daily_mission_flags(p92)
    local v96 = v_u_4
    local v97
    if p91 > 0 then
        v97 = p91 <= 32
    else
        v97 = false
    end;
    v96:is_true(v97)
    if v_u_5.And(v95, v_u_5.LShift(1, p91 - 1)) ~= 0 == true then
        return 0;
    end;
    local v98 = v_u_7:playerblob_get_daily_mission_points(p92)
    local v99 = math.min(v98 + v_u_10:get(p91), v_u_7:get_daily_point_cap()) - v98
    local l_CPV2DayFlags_0 = p92.CPV2DayFlags
    local v100 = v_u_4
    local v101
    if p91 > 0 then
        v101 = p91 <= 32
    else
        v101 = false
    end;
    v100:is_true(v101)
    p92.CPV2DayFlags = v_u_5.Or(l_CPV2DayFlags_0, v_u_5.LShift(1, p91 - 1))
    if v99 > 0 then
        p92.CPV2Points = p92.CPV2Points + v99
    end;
    return v99;
end;
v_u_7.weekly_mission_type_playerblob_claim_weekid_monthid = function(_, p102, p103, p104, p105) --[[ Name: weekly_mission_type_playerblob_claim_weekid_monthid ]] --[[ Line: 277 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_4, (copy 4): v_u_7, (copy 5): v_u_5, (copy 6): v_u_15 ]]
    if p103.CPV2MonthID ~= p105 then
        p103.CPV2MonthID = p105
        p103.CPV2Points = 0
        p103.CPV2MonthUpgradeToVIP = false
        p103.CPV2StandardClaimedTier = 0
        p103.CPV2VIPClaimedTier = 0
        if v_u_1:is_dev_build() then
            v_u_3:puts("ChallengePassV2Mission:playerblob_validate_monthid reset monthid(%d)", p105)
        end;
    end;
    if p103.CPV2WeekID ~= p104 then
        p103.CPV2WeekID = p104
        p103.CPV2WeekFlags = 0
        if v_u_1:is_dev_build() then
            v_u_3:puts("ChallengePassV2Mission:weekly_mission_type_playerblob_claim_weekid reset weekid(%d)", p104)
        end;
    end;
    if p103.CPV2WeekID ~= p104 then
        p103.CPV2WeekID = p104
        p103.CPV2WeekFlags = 0
        if v_u_1:is_dev_build() then
            v_u_3:warnf("ChallengePassV2Mission:weekly_mission_type_playerblob_claim_weekid reset weekid(%d)", p104)
        end;
    end;
    if v_u_4:test_enum_member(p102, v_u_7.WeeklyMissionType) ~= true then
        v_u_3:warnf("ChallengePassV2Mission:weekly_mission_type_playerblob_claim is not enum member(%s)", (tostring(p102)))
        return 0;
    end;
    local v106 = v_u_7:playerblob_get_weekly_mission_flags(p103)
    local v107 = v_u_4
    local v108
    if p102 > 0 then
        v108 = p102 <= 32
    else
        v108 = false
    end;
    v107:is_true(v108)
    if v_u_5.And(v106, v_u_5.LShift(1, p102 - 1)) ~= 0 == true then
        return 0;
    end;
    local v109 = v_u_7:playerblob_get_weekly_mission_points(p103)
    local v110 = math.min(v109 + v_u_15:get(p102), v_u_7:get_weekly_point_cap()) - v109
    local l_CPV2WeekFlags_0 = p103.CPV2WeekFlags
    local v111 = v_u_4
    local v112
    if p102 > 0 then
        v112 = p102 <= 32
    else
        v112 = false
    end;
    v111:is_true(v112)
    p103.CPV2WeekFlags = v_u_5.Or(l_CPV2WeekFlags_0, v_u_5.LShift(1, p102 - 1))
    if v110 > 0 then
        p103.CPV2Points = p103.CPV2Points + v110
    end;
    return v110;
end;
return v_u_7;
