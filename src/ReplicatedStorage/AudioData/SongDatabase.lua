-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:44 PM
-- Time elapsed: 26 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_5 = require(game.ReplicatedStorage.AudioData.SongErrorParser)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_8 = require(game.ReplicatedStorage.AudioData.AudioMod)
local v_u_9 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_10 = require(game.ReplicatedStorage.AudioData.SongDatabaseData)
require(game.ReplicatedStorage.PlayerInfo.TutorialInfo)
local v_u_11 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_12 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_13 = require(game.ReplicatedStorage.Shared.CurveUtil)
local s_RunService_0 = game:GetService("RunService")
local v14 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_15 = nil
v14:require_shared(function() --[[ Line: 19 ]]
    --[[ Upvalues: (ref 1): v_u_15 ]]
    v_u_15 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
end)
local l_SongDatabaseLoad_0 = game.ReplicatedStorage.Events.SongDatabaseLoad
local v_u_16 = v_u_1:new()
local v_u_17 = v_u_15
for _, v18 in pairs(game.ReplicatedStorage.AudioData.SongDataHeaders:GetChildren()) do
    v_u_16:push_back(v18)
end;
local v_u_19 = {}
local l_PreloadedSongs_0 = game.ReplicatedStorage.AudioData.PreloadedSongs
local v_u_20 = require(l_PreloadedSongs_0.WelcomeToMondayNightIntroDEBUG)
local v_u_21 = v_u_1:new()
v_u_19.preloaded_data_placeholder = function(_) --[[ Name: preloaded_data_placeholder ]] --[[ Line: 35 ]]
    --[[ Upvalues: (copy 1): v_u_21 ]]
    return v_u_21:random();
end;
local v22 = game:FindFirstChild("ServerScriptService")
local v_u_23
if v22 then
    v_u_23 = v22:FindFirstChild("NewSong")
else
    v_u_23 = nil
end;
v_u_19.MOD_NORMAL = v_u_8.Normal
v_u_19.MOD_HARDMODE = v_u_8.Hard
v_u_19.MOD_EASY = v_u_8.Easy
v_u_19.NORMAL_COMBINE_COUNT = 5
v_u_19.SongPriority = {
    ["Hidden"] = 0,
    ["NoSongShop"] = 1,
    ["Normal"] = 2
}
v_u_19.new = function(_) --[[ Name: new ]] --[[ Line: 55 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1, (copy 3): v_u_7, (copy 4): v_u_3, (copy 5): v_u_20, (copy 6): v_u_6, (copy 7): v_u_19, (copy 8): l_PreloadedSongs_0, (ref 9): v_u_23, (copy 10): v_u_10, (copy 11): v_u_16, (copy 12): v_u_21, (copy 13): v_u_5, (copy 14): v_u_8, (copy 15): v_u_11, (copy 16): l_SongDatabaseLoad_0, (copy 17): v_u_12, (copy 18): s_RunService_0, (copy 19): v_u_13, (copy 20): v_u_4, (copy 21): v_u_9, (ref 22): v_u_17 ]]
    local v_u_24 = v_u_2:new()
    local v_u_25 = v_u_1:new()
    local v_u_26 = v_u_2:new()
    local v_u_27 = v_u_2:new()
    local v_u_28 = v_u_2:new()
    local v_u_29 = v_u_2:new()
    local v_u_30 = v_u_2:new()
    local v_u_31 = v_u_2:new()
    local v_u_32 = v_u_2:new()
    local v_u_33 = v_u_2:new()
    local function _(p34) --[[ Name: get_data_for_key_unloaded ]] --[[ Line: 71 ]]
        --[[ Upvalues: (copy 1): v_u_24, (ref 2): v_u_7, (ref 3): v_u_3, (ref 4): v_u_20 ]]
        local v35 = v_u_24:get(p34)
        if v35 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
            v35.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p34 then
            v35.AudioAssetId = v_u_20.AudioAssetId
        end;
        return v35;
    end;
    local function _(p36) --[[ Name: calculate_hitcount_from_hitobjects ]] --[[ Line: 82 ]]
        local v37 = 0
        for v38 = 1, #p36 do
            if p36[v38].Type == 1 then
                v37 = v37 + 1
            else
                v37 = v37 + 2
            end;
        end;
        return v37;
    end;
    local function _(p39) --[[ Name: calculate_hit_objects_count_from_hitobjects ]] --[[ Line: 95 ]]
        return #p39;
    end;
    local function _(p40) --[[ Name: calculate_last_note_time_from_hitobjects ]] --[[ Line: 99 ]]
        return p40[#p40].Time;
    end;
    local v41 = v_u_20
    local l_HitObjects_0 = v_u_20.HitObjects
    local v42 = 0
    local v_u_43 = {}
    for v44 = 1, #l_HitObjects_0 do
        if l_HitObjects_0[v44].Type == 1 then
            v42 = v42 + 1
        else
            v42 = v42 + 2
        end;
    end;
    v41.HitCount = v42
    local v45 = v_u_20
    local l_HitObjects_1 = v_u_20.HitObjects
    v45.LastNoteTime = l_HitObjects_1[#l_HitObjects_1].Time
    v_u_20.HitObjectsCount = #v_u_20.HitObjects
    local function f_write_loaded_song_data_to_key(p46, p47) --[[ Name: write_loaded_song_data_to_key ]] --[[ Line: 109 ]]
        --[[ Upvalues: (copy 1): v_u_24, (ref 2): v_u_7, (ref 3): v_u_3, (ref 4): v_u_20, (ref 5): v_u_6, (ref 6): v_u_19 ]]
        local v48 = v_u_24:get(p46)
        if v48 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
            v48.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p46 then
            v48.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v48 == nil then
            if p47 == nil then
                v_u_6:warnf("ERROR: SongDatabase:write_loaded_song_data_to_key nil loaded_song_data, falling back to preloaded data")
                return v_u_19:preloaded_data_placeholder();
            end;
            v_u_24:add(p46, p47)
            v48 = p47
        end;
        v48.Loaded = true
        v48.HitObjects = p47.HitObjects
        v48.TimingPoints = p47.TimingPoints
        if v_u_3:is_dev_build() and v_u_7.SwapDebugSong == true then
            v_u_6:warnf("DebugConfig.SwapDebugSong loading song(%d) with debug data", p46)
            v48.HitObjects = v_u_20.HitObjects
            v48.TimingPoints = v_u_20.TimingPoints
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p46 then
            v48.HitObjects = v_u_20.HitObjects
            v48.TimingPoints = v_u_20.TimingPoints
        end;
        if v48.HitCount == nil then
            local l_HitObjects_2 = v48.HitObjects
            local v49 = 0
            for v50 = 1, #l_HitObjects_2 do
                if l_HitObjects_2[v50].Type == 1 then
                    v49 = v49 + 1
                else
                    v49 = v49 + 2
                end;
            end;
            v48.HitCount = v49
        end;
        if v48.LastNoteTime == nil then
            local l_HitObjects_3 = v48.HitObjects
            v48.LastNoteTime = l_HitObjects_3[#l_HitObjects_3].Time
        end;
        if v48.HitObjectsCount == nil then
            v48.HitObjectsCount = #v48.HitObjects
        end;
        return v48;
    end;
    local function f_load_song_key_modulescript(p51) --[[ Name: load_song_key_modulescript ]] --[[ Line: 147 ]]
        --[[ Upvalues: (copy 1): v_u_33, (ref 2): v_u_6, (copy 3): f_write_loaded_song_data_to_key ]]
        if v_u_33:contains(p51) ~= true then
            v_u_6:errf("_songkey_to_modulescript not contain(%s)", p51)
        end;
        return f_write_loaded_song_data_to_key(p51, (require((v_u_33:get(p51)))));
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 154 ]]
        --[[ Upvalues: (ref 1): l_PreloadedSongs_0, (ref 2): v_u_23, (ref 3): v_u_10, (ref 4): v_u_6, (ref 5): v_u_2, (copy 6): v_u_33, (copy 7): v_u_25, (copy 8): v_u_26, (ref 9): v_u_1, (ref 10): v_u_16, (copy 11): v_u_43, (copy 12): f_load_song_key_modulescript, (ref 13): v_u_21, (ref 14): v_u_3, (ref 15): v_u_7, (copy 16): v_u_24, (ref 17): v_u_20, (ref 18): v_u_5, (ref 19): v_u_19, (ref 20): v_u_8, (copy 21): v_u_29, (copy 22): v_u_30, (copy 23): v_u_31, (copy 24): v_u_32, (copy 25): v_u_27, (copy 26): v_u_28 ]]
        local v52 = tick()
        local function _(p53) --[[ Name: find_song_modulescript_by_name ]] --[[ Line: 157 ]]
            --[[ Upvalues: (ref 1): l_PreloadedSongs_0, (ref 2): v_u_23 ]]
            local v54 = l_PreloadedSongs_0:FindFirstChild(p53)
            if v54 ~= nil then
                return v54;
            end;
            if v_u_23 then
                v54 = v_u_23:FindFirstChild(p53)
            end;
            return v54;
        end;
        if #v_u_10 > 50000 then
            v_u_6:errf("Need to update PlayerSongStatCollection to support >50k songs, current(%d)", #v_u_10)
        end;
        local v55 = v_u_2:new()
        for v56 = 1, #v_u_10 do
            local v57 = v_u_10[v56]
            local v58 = l_PreloadedSongs_0:FindFirstChild(v57)
            if v58 == nil then
                if v_u_23 then
                    v58 = v_u_23:FindFirstChild(v57)
                end;
            end;
            if v58 then
                v_u_33:add(v56, v58)
            end;
            v_u_25:push_back(v56)
            v55:add_set(v57)
            v_u_26:add(v57, v56)
        end;
        local v59 = v_u_1:new()
        for _, v60 in v_u_16:key_itr() do
            v59:push_back(require(v60))
        end;
        for _, v61 in v59:key_itr() do
            for v62, v63 in pairs(v61) do
                if v_u_26:contains(v62) then
                    local v64 = v_u_26:get(v62)
                    v55:remove(v62)
                    v63.HitObjects = {}
                    v63.TimingPoints = {}
                    v63.Loaded = false
                    v_u_43:add_key_to_data(v64, v63)
                end;
            end;
        end;
        for v65, _ in v55:key_itr() do
            if v_u_26:contains(v65) ~= true then
                v_u_6:errf("_name_to_key not contain(%s)", v65)
            end;
            v_u_21:push_back((f_load_song_key_modulescript((v_u_26:get(v65)))))
        end;
        if v_u_3:is_dev_build() and (v_u_7.DevRunSongErrorParser == true and v_u_23 ~= nil) then
            local v66 = tick()
            for v67 = 1, #v_u_10 do
                local v_u_68 = v_u_10[v67]
                local v69 = v_u_26:get(v_u_68)
                local v70 = v_u_24:get(v69)
                if v70 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
                    v70.AudioAssetId = v_u_20.AudioAssetId
                end;
                if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == v69 then
                    v70.AudioAssetId = v_u_20.AudioAssetId
                end;
                local l_Loaded_0 = v70.Loaded
                local v_u_71 = f_load_song_key_modulescript(v69)
                local v72, v73 = pcall(function() --[[ Line: 218 ]]
                    --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_68, (copy 3): v_u_71 ]]
                    v_u_5:scan_audiodata_for_errors(v_u_68, v_u_71)
                end)
                if v72 ~= true then
                    v_u_6:errf("SongErrorParser failed[%d](%s) message(%s)", v69, v_u_68, v73)
                end;
                local l_HitObjects_4 = v_u_71.HitObjects
                local v74 = 0
                for v75 = 1, #l_HitObjects_4 do
                    if l_HitObjects_4[v75].Type == 1 then
                        v74 = v74 + 1
                    else
                        v74 = v74 + 2
                    end;
                end;
                if v74 ~= v_u_71.HitCount then
                    v_u_6:errf("mismatched calc_hitcount(%d) audio_data.HitCount(%d)", v74, v_u_71.HitCount)
                end;
                local v76 = #v_u_71.HitObjects
                if v76 ~= v_u_71.HitObjectsCount then
                    v_u_6:errf("mismatched calc_hitobjects_count(%d) audio_data.HitCount(%d)", v76, v_u_71.HitObjectsCount)
                end;
                if l_Loaded_0 ~= true then
                    v_u_71.Loaded = false
                    v_u_71.HitObjects = {}
                    v_u_71.TimingPoints = {}
                end;
            end;
            v_u_6:puts("DEV-SongErrorParser completed in (%.2f)", tick() - v66)
        end;
        for v77 = 1, #v_u_10 do
            local v78 = v_u_10[v77]
            if v_u_26:contains(v78) ~= true then
                v_u_6:errf("_name_to_key does not contain(%s)", v78)
            end;
            local v79 = v_u_26:get(v78)
            local v80 = v_u_24:get(v79)
            if v80 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
                v80.AudioAssetId = v_u_20.AudioAssetId
            end;
            if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == v79 then
                v80.AudioAssetId = v_u_20.AudioAssetId
            end;
            if v80.HitCount == nil then
                v_u_6:errf("audio_data(%s) does not contain HitCount", v78)
            end;
            if v80.LastNoteTime == nil then
                v_u_6:errf("audio_data(%s) does not contain LastNoteTime", v78)
            end;
            if v80.HitObjectsCount == nil then
                v_u_6:errf("audio_data(%s) does not contain HitObjectsCount", v78)
            end;
            if v80.BPM == nil then
                v_u_6:errf("audio_data(%s) does not contain BPM", v78)
            end;
            if v80.Priority == v_u_19.SongPriority.Hidden and v80.IsRemix ~= true then
                v_u_6:errf("song(%s) priority is hidden but not IsRemix flagged", v78)
            end;
            local v81 = v80.AudioMod == v_u_8.Easy
            if v81 and v_u_43:key_is_remix_flagged(v79) ~= true then
                v_u_29:add(v79, true)
            end;
            if v80.FusionResult ~= nil and #v80.FusionResult > 0 then
                local l_FusionResult_0 = v80.FusionResult
                if v_u_26:contains(l_FusionResult_0) == false then
                    error("Unknown fusion result " .. tostring(l_FusionResult_0) .. " for " .. tostring(v78))
                end;
                local v82 = v_u_26:get(l_FusionResult_0)
                if v81 then
                    v_u_30:add(v82, true)
                    v_u_31:add(v82, v79)
                    v_u_32:add(v79, v82)
                else
                    v_u_27:add(v79, {
                        ["RequiredCount"] = v_u_19.NORMAL_COMBINE_COUNT,
                        ["OutputKey"] = v82
                    })
                    v_u_28:add(v82, v79)
                end;
            end;
        end;
        for v83, v84 in v_u_31:key_itr() do
            if v_u_27:contains(v83) then
                v_u_31:add(v_u_27:get(v83).OutputKey, v84)
            end;
        end;
        v_u_6:puts("SongDatabase loaded in(%.3f), initial load(%d)", tick() - v52, v55:count())
    end;
    local v_u_85 = -1
    v_u_43.set_server_id = function(_, p86) --[[ Name: set_server_id ]] --[[ Line: 333 ]]
        --[[ Upvalues: (ref 1): v_u_85 ]]
        v_u_85 = p86
    end;
    local v_u_87 = nil
    local v_u_88 = nil
    local v_u_89 = -1
    local v_u_90 = -1
    v_u_43.set_as_client = function(_, p91) --[[ Name: set_as_client ]] --[[ Line: 341 ]]
        --[[ Upvalues: (ref 1): v_u_88, (ref 2): v_u_87, (ref 3): v_u_6, (ref 4): v_u_89, (ref 5): v_u_90, (copy 6): f_write_loaded_song_data_to_key, (ref 7): v_u_11, (ref 8): l_SongDatabaseLoad_0 ]]
        v_u_88 = p91
        v_u_87 = true
        local function _(p92, p93) --[[ Name: handle_response ]] --[[ Line: 344 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_89, (ref 3): v_u_90, (ref 4): f_write_loaded_song_data_to_key ]]
            v_u_6:puts("SongDatabaseLoad response received(%s)", (tostring(p92)))
            v_u_89 = tick()
            v_u_90 = p92
            f_write_loaded_song_data_to_key(p92, p93).WasRemoteLoaded = true
        end;
        v_u_88:wait_on_event(v_u_11.EVT_SongDatabase_ServerLoadResponse, function(p94, p95) --[[ Line: 351 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_89, (ref 3): v_u_90, (ref 4): f_write_loaded_song_data_to_key ]]
            v_u_6:puts("SongDatabaseLoad response received(%s)", (tostring(p94)))
            v_u_89 = tick()
            v_u_90 = p94
            f_write_loaded_song_data_to_key(p94, p95).WasRemoteLoaded = true
        end)
        l_SongDatabaseLoad_0.OnClientEvent:connect(function(p96, p97) --[[ Line: 354 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_89, (ref 3): v_u_90, (ref 4): f_write_loaded_song_data_to_key ]]
            v_u_6:puts("SongDatabaseLoad response received(%s)", (tostring(p96)))
            v_u_89 = tick()
            v_u_90 = p96
            f_write_loaded_song_data_to_key(p96, p97).WasRemoteLoaded = true
        end)
    end;
    v_u_43.set_as_server = function(p_u_98, p99) --[[ Name: set_as_server ]] --[[ Line: 359 ]]
        --[[ Upvalues: (ref 1): v_u_88, (ref 2): v_u_87, (ref 3): v_u_12, (ref 4): v_u_2, (ref 5): v_u_7, (ref 6): v_u_6, (ref 7): v_u_19, (ref 8): l_SongDatabaseLoad_0, (ref 9): v_u_11, (ref 10): s_RunService_0, (ref 11): v_u_13 ]]
        v_u_88 = p99
        v_u_87 = false
        local v_u_100 = v_u_12:new()
        local v_u_101 = v_u_2:new()
        local v_u_102 = v_u_2:new()
        local v_u_103 = 0
        local function f_handle_request(p_u_104, p_u_105) --[[ Name: handle_request ]] --[[ Line: 366 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_103, (ref 3): v_u_6, (copy 4): v_u_100, (copy 5): v_u_101, (ref 6): v_u_19, (copy 7): v_u_102, (copy 8): p_u_98, (ref 9): l_SongDatabaseLoad_0, (ref 10): v_u_88, (ref 11): v_u_11 ]]
            if v_u_7.DEBUG_SongDatabaseRemoteLoadFail == true then
                v_u_103 = v_u_103 + 1
                if v_u_103 % 9 ~= 0 then
                    return v_u_6:warnf("DEBUG_SongDatabaseRemoteLoadFail(%d/%d)", v_u_103, 9);
                end;
            end;
            if v_u_100:is_on_cooldown(p_u_104.UserId) then
                return v_u_6:warnf("SongDatabaseLoad.OnServerEvent cooldown for(%d)", p_u_104.UserId);
            end;
            local v106 = v_u_101:get(p_u_104.UserId)
            if v106 == nil then
                v106 = v_u_19:invalid_songkey()
            end;
            local v107 = v_u_102:get(p_u_104.UserId)
            local v108 = v107 == nil and 0 or v107
            if p_u_105 == v106 then
                v_u_102:add(p_u_104.UserId, v108 + 1)
                if v108 > 0 and v108 % 4 ~= 0 then
                    return v_u_6:warnf("SongDatabaseLoad.OnServerEvent player(%s) last_requested_songkey_count(%d) skip resend", p_u_104.Name, v108);
                end;
            else
                v_u_101:add(p_u_104.UserId, p_u_105)
                v_u_102:add(p_u_104.UserId, 1)
            end;
            local function _() --[[ Name: response ]] --[[ Line: 390 ]]
                --[[ Upvalues: (ref 1): v_u_100, (copy 2): p_u_104, (ref 3): p_u_98, (copy 4): p_u_105, (ref 5): v_u_7, (ref 6): l_SongDatabaseLoad_0, (ref 7): v_u_88, (ref 8): v_u_11 ]]
                v_u_100:add_cooldown_to_id(p_u_104.UserId, 0.5)
                p_u_98:get_data_for_key(p_u_105, function(p109) --[[ Line: 392 ]]
                    --[[ Upvalues: (ref 1): v_u_7, (ref 2): l_SongDatabaseLoad_0, (ref 3): p_u_104, (ref 4): p_u_105, (ref 5): v_u_88, (ref 6): v_u_11 ]]
                    if v_u_7.SongDatabaseLoadRemoteEvent == true then
                        l_SongDatabaseLoad_0:FireClient(p_u_104, p_u_105, p109)
                    else
                        v_u_88:fire_event_to_client(v_u_11.EVT_SongDatabase_ServerLoadResponse, p_u_104, p_u_105, p109)
                    end;
                end)
            end;
            v_u_100:add_cooldown_to_id(p_u_104.UserId, 0.5)
            p_u_98:get_data_for_key(p_u_105, function(p110) --[[ Line: 392 ]]
                --[[ Upvalues: (ref 1): v_u_7, (ref 2): l_SongDatabaseLoad_0, (copy 3): p_u_104, (copy 4): p_u_105, (ref 5): v_u_88, (ref 6): v_u_11 ]]
                if v_u_7.SongDatabaseLoadRemoteEvent == true then
                    l_SongDatabaseLoad_0:FireClient(p_u_104, p_u_105, p110)
                else
                    v_u_88:fire_event_to_client(v_u_11.EVT_SongDatabase_ServerLoadResponse, p_u_104, p_u_105, p110)
                end;
            end)
        end;
        v_u_88:wait_on_event(v_u_11.EVT_SongDatabase_ClientRequestLoad, function(p111, p112) --[[ Line: 403 ]]
            --[[ Upvalues: (copy 1): f_handle_request ]]
            f_handle_request(p111, p112)
        end)
        l_SongDatabaseLoad_0.OnServerEvent:connect(function(p113, p114) --[[ Line: 406 ]]
            --[[ Upvalues: (copy 1): f_handle_request ]]
            f_handle_request(p113, p114)
        end)
        s_RunService_0.Heartbeat:Connect(function(p115) --[[ Line: 410 ]]
            --[[ Upvalues: (ref 1): v_u_13, (copy 2): v_u_100 ]]
            v_u_100:update((v_u_13:DeltaTimeToTimescale(p115)))
        end)
    end;
    local v_u_116 = 0
    local v_u_117 = 0
    v_u_43.get_loading_retry_count_and_wait_time = function(_) --[[ Name: get_loading_retry_count_and_wait_time ]] --[[ Line: 418 ]]
        --[[ Upvalues: (ref 1): v_u_116, (ref 2): v_u_117 ]]
        return v_u_116, v_u_117;
    end;
    local v_u_118 = v_u_4:new()
    local v_u_119 = 0
    local v_u_120 = 0
    local function f_client_load_song_data(p_u_121, p122) --[[ Name: client_load_song_data ]] --[[ Line: 425 ]]
        --[[ Upvalues: (ref 1): v_u_116, (ref 2): v_u_117, (copy 3): v_u_24, (ref 4): v_u_7, (ref 5): v_u_3, (ref 6): v_u_20, (copy 7): v_u_118, (ref 8): l_SongDatabaseLoad_0, (ref 9): v_u_88, (ref 10): v_u_11, (ref 11): v_u_119, (ref 12): v_u_120, (ref 13): v_u_89, (ref 14): v_u_90, (ref 15): v_u_85, (ref 16): v_u_6, (copy 17): f_load_song_key_modulescript ]]
        v_u_116 = 0
        v_u_117 = 0
        local v123 = v_u_24:get(p_u_121)
        if v123 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
            v123.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p_u_121 then
            v123.AudioAssetId = v_u_20.AudioAssetId
        end;
        local v_u_124 = v123
        local v125 = v_u_118:list_of(p_u_121):count()
        v_u_118:push_back_to(p_u_121, p122)
        if v125 == 0 then
            local function f_run_pending_callbacks_with_data(p126) --[[ Name: run_pending_callbacks_with_data ]] --[[ Line: 432 ]]
                --[[ Upvalues: (ref 1): v_u_118, (copy 2): p_u_121 ]]
                for _, v127 in v_u_118:list_of(p_u_121):key_itr() do
                    v127(p126)
                end;
                v_u_118:list_of(p_u_121):clear()
            end;
            local function _() --[[ Name: fire_event ]] --[[ Line: 438 ]]
                --[[ Upvalues: (ref 1): v_u_7, (ref 2): l_SongDatabaseLoad_0, (copy 3): p_u_121, (ref 4): v_u_88, (ref 5): v_u_11 ]]
                if v_u_7.SongDatabaseLoadRemoteEvent == true then
                    l_SongDatabaseLoad_0:FireServer(p_u_121)
                else
                    v_u_88:fire_event_to_server(v_u_11.EVT_SongDatabase_ClientRequestLoad, p_u_121)
                end;
            end;
            local v_u_128 = tick()
            local function _(p129) --[[ Name: get_song_database_load_errstr ]] --[[ Line: 447 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_119, (ref 3): v_u_120, (copy 4): v_u_128, (ref 5): v_u_89, (ref 6): v_u_90, (ref 7): v_u_85 ]]
                return v_u_3:table_to_string({
                    ["Version"] = 4,
                    ["LoadedCount"] = v_u_119,
                    ["ErrorCount"] = v_u_120,
                    ["TimeStart"] = v_u_128,
                    ["TimeServerLoadResponse"] = v_u_89,
                    ["ServerLoadLastKey"] = v_u_90,
                    ["ServerID"] = v_u_85,
                    ["WaitTime"] = p129
                });
            end;
            local function _(p_u_130, p_u_131, p_u_132, p_u_133) --[[ Name: wait_on_loaded_with_retry ]] --[[ Line: 460 ]]
                --[[ Upvalues: (ref 1): v_u_7, (ref 2): l_SongDatabaseLoad_0, (copy 3): p_u_121, (ref 4): v_u_88, (ref 5): v_u_11, (ref 6): v_u_116, (ref 7): v_u_6, (ref 8): v_u_117, (ref 9): v_u_124, (ref 10): v_u_24, (ref 11): v_u_3, (ref 12): v_u_20 ]]
                spawn(function() --[[ Line: 461 ]]
                    --[[ Upvalues: (copy 1): p_u_131, (ref 2): v_u_7, (ref 3): l_SongDatabaseLoad_0, (ref 4): p_u_121, (ref 5): v_u_88, (ref 6): v_u_11, (ref 7): v_u_116, (ref 8): v_u_6, (copy 9): p_u_130, (ref 10): p_u_133, (ref 11): v_u_117, (ref 12): v_u_124, (ref 13): v_u_24, (ref 14): v_u_3, (ref 15): v_u_20, (copy 16): p_u_132 ]]
                    local v134 = 0
                    local v135 = 0
                    while p_u_131() do
                        local v136 = v134 + 0.25
                        v135 = v135 + 0.25
                        if v135 >= 5 then
                            if v_u_7.SongDatabaseLoadRemoteEvent == true then
                                l_SongDatabaseLoad_0:FireServer(p_u_121)
                            else
                                v_u_88:fire_event_to_server(v_u_11.EVT_SongDatabase_ClientRequestLoad, p_u_121)
                            end;
                            v_u_116 = v_u_116 + 1
                            v_u_6:warnf("SongDatabase:get_data_for_key(%d) wait_on_loaded_with_retry retry(%.2f)", p_u_121, v136)
                            v135 = 0
                        end;
                        if p_u_130 <= v136 and (v134 < p_u_130 and p_u_133) then
                            p_u_133(v136)
                            p_u_133 = nil
                        end;
                        wait(0.25)
                        v_u_117 = v_u_117 + 0.25
                        local v137 = p_u_121
                        local v138 = v_u_24:get(v137)
                        if v138 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
                            v138.AudioAssetId = v_u_20.AudioAssetId
                        end;
                        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == v137 then
                            v138.AudioAssetId = v_u_20.AudioAssetId
                        end;
                        v_u_124 = v138
                        v134 = v136
                    end;
                    p_u_132(v134)
                end)
            end;
            local function v_u_139() --[[ Line: 492 ]]
                --[[ Upvalues: (ref 1): v_u_124 ]]
                return v_u_124.Loaded ~= true;
            end;
            local function v_u_141(p140) --[[ Line: 495 ]]
                --[[ Upvalues: (ref 1): v_u_124, (ref 2): v_u_3, (ref 3): v_u_119, (ref 4): v_u_120, (copy 5): v_u_128, (ref 6): v_u_89, (ref 7): v_u_90, (ref 8): v_u_85, (ref 9): v_u_6, (copy 10): p_u_121, (copy 11): f_run_pending_callbacks_with_data, (ref 12): v_u_88, (ref 13): v_u_11 ]]
                if v_u_124.Loaded ~= true then
                    return v_u_6:warnf("Client SongDatabase load(%d) failed to load from remote (%s)", p_u_121, (v_u_3:table_to_string({
                        ["Version"] = 4,
                        ["LoadedCount"] = v_u_119,
                        ["ErrorCount"] = v_u_120,
                        ["TimeStart"] = v_u_128,
                        ["TimeServerLoadResponse"] = v_u_89,
                        ["ServerLoadLastKey"] = v_u_90,
                        ["ServerID"] = v_u_85,
                        ["WaitTime"] = p140
                    })));
                end;
                v_u_119 = v_u_119 + 1
                v_u_6:puts("Client SongDatabase load(%d), loaded total(%d) time(%.2f)...", p_u_121, v_u_119, p140)
                f_run_pending_callbacks_with_data(v_u_124)
                if p140 > 15 then
                    v_u_88:fire_event_to_server(v_u_11.EVT_EventReport_ClientReportEvent, 3015, p_u_121, (v_u_3:table_to_string({
                        ["Version"] = 4,
                        ["LoadedCount"] = v_u_119,
                        ["ErrorCount"] = v_u_120,
                        ["TimeStart"] = v_u_128,
                        ["TimeServerLoadResponse"] = v_u_89,
                        ["ServerLoadLastKey"] = v_u_90,
                        ["ServerID"] = v_u_85,
                        ["WaitTime"] = p140
                    })))
                end;
            end;
            local function v_u_145(p142) --[[ Line: 509 ]]
                --[[ Upvalues: (ref 1): v_u_120, (ref 2): v_u_7, (ref 3): f_load_song_key_modulescript, (copy 4): p_u_121, (copy 5): f_run_pending_callbacks_with_data, (ref 6): v_u_3, (ref 7): v_u_119, (copy 8): v_u_128, (ref 9): v_u_89, (ref 10): v_u_90, (ref 11): v_u_85, (ref 12): v_u_6, (ref 13): v_u_88, (ref 14): v_u_11 ]]
                v_u_120 = v_u_120 + 1
                if v_u_7.SongDatabaseRemoteLoadOnly == false then
                    local v_u_143 = nil
                    pcall(function() --[[ Line: 514 ]]
                        --[[ Upvalues: (ref 1): v_u_143, (ref 2): f_load_song_key_modulescript, (ref 3): p_u_121 ]]
                        v_u_143 = f_load_song_key_modulescript(p_u_121)
                    end)
                    if v_u_143 ~= nil then
                        f_run_pending_callbacks_with_data(v_u_143)
                    end;
                end;
                local v144 = v_u_3:table_to_string({
                    ["Version"] = 4,
                    ["LoadedCount"] = v_u_119,
                    ["ErrorCount"] = v_u_120,
                    ["TimeStart"] = v_u_128,
                    ["TimeServerLoadResponse"] = v_u_89,
                    ["ServerLoadLastKey"] = v_u_90,
                    ["ServerID"] = v_u_85,
                    ["WaitTime"] = p142
                })
                v_u_6:warnf("Reporting timed out SongDatabase load(%s)", v144)
                v_u_88:fire_event_to_server(v_u_11.EVT_EventReport_ClientReportEvent, 3014, p_u_121, v144)
            end;
            local v_u_146 = 15
            spawn(function() --[[ Line: 461 ]]
                --[[ Upvalues: (copy 1): v_u_139, (ref 2): v_u_7, (ref 3): l_SongDatabaseLoad_0, (copy 4): p_u_121, (ref 5): v_u_88, (ref 6): v_u_11, (ref 7): v_u_116, (ref 8): v_u_6, (copy 9): v_u_146, (ref 10): v_u_145, (ref 11): v_u_117, (ref 12): v_u_124, (ref 13): v_u_24, (ref 14): v_u_3, (ref 15): v_u_20, (copy 16): v_u_141 ]]
                local v147 = 0
                local v148 = 0
                while v_u_139() do
                    local v149 = v147 + 0.25
                    v148 = v148 + 0.25
                    if v148 >= 5 then
                        if v_u_7.SongDatabaseLoadRemoteEvent == true then
                            l_SongDatabaseLoad_0:FireServer(p_u_121)
                        else
                            v_u_88:fire_event_to_server(v_u_11.EVT_SongDatabase_ClientRequestLoad, p_u_121)
                        end;
                        v_u_116 = v_u_116 + 1
                        v_u_6:warnf("SongDatabase:get_data_for_key(%d) wait_on_loaded_with_retry retry(%.2f)", p_u_121, v149)
                        v148 = 0
                    end;
                    if v_u_146 <= v149 and (v147 < v_u_146 and v_u_145) then
                        v_u_145(v149)
                        v_u_145 = nil
                    end;
                    wait(0.25)
                    v_u_117 = v_u_117 + 0.25
                    local v150 = p_u_121
                    local v151 = v_u_24:get(v150)
                    if v151 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
                        v151.AudioAssetId = v_u_20.AudioAssetId
                    end;
                    if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == v150 then
                        v151.AudioAssetId = v_u_20.AudioAssetId
                    end;
                    v_u_124 = v151
                    v147 = v149
                end;
                v_u_141(v147)
            end)
            if v_u_7.SongDatabaseLoadRemoteEvent == true then
                l_SongDatabaseLoad_0:FireServer(p_u_121)
            else
                v_u_88:fire_event_to_server(v_u_11.EVT_SongDatabase_ClientRequestLoad, p_u_121)
            end;
        end;
    end;
    v_u_43.get_data_for_key = function(_, p152, p153) --[[ Name: get_data_for_key ]] --[[ Line: 531 ]]
        --[[ Upvalues: (copy 1): v_u_24, (ref 2): v_u_7, (ref 3): v_u_3, (ref 4): v_u_20, (ref 5): v_u_87, (ref 6): v_u_19, (copy 7): v_u_118, (copy 8): f_client_load_song_data, (ref 9): v_u_119, (ref 10): v_u_6, (copy 11): f_load_song_key_modulescript ]]
        local v154 = v_u_24:get(p152)
        if v154 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
            v154.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p152 then
            v154.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v154 == nil then
            return p153(nil);
        elseif v_u_87 then
            if v_u_19:singleton():is_key_data_loaded(p152) then
                return p153(v154);
            elseif v_u_118:list_of(p152):count() > 0 then
                return v_u_118:push_back_to(p152, p153);
            else
                return f_client_load_song_data(p152, p153);
            end;
        else
            if v_u_19:singleton():is_key_data_loaded(p152) == true then
                return p153(v154);
            end;
            v_u_119 = v_u_119 + 1
            v_u_6:puts("Server SongDatabase load(%d) loaded total(%d)...", p152, v_u_119)
            return p153(f_load_song_key_modulescript(p152));
        end;
    end;
    v_u_43.is_key_data_loaded = function(_, p155) --[[ Name: is_key_data_loaded ]] --[[ Line: 554 ]]
        --[[ Upvalues: (copy 1): v_u_24, (ref 2): v_u_7, (ref 3): v_u_3, (ref 4): v_u_20 ]]
        local v156 = v_u_24:get(p155)
        if v156 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
            v156.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p155 then
            v156.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v156 == nil then
            return false;
        else
            return v156.Loaded;
        end;
    end;
    v_u_43.name_to_key_itr = function(_) --[[ Name: name_to_key_itr ]] --[[ Line: 560 ]]
        --[[ Upvalues: (copy 1): v_u_26 ]]
        return v_u_26:key_itr();
    end;
    v_u_43.name_to_key = function(_, p157) --[[ Name: name_to_key ]] --[[ Line: 564 ]]
        --[[ Upvalues: (copy 1): v_u_26 ]]
        return v_u_26:get(p157);
    end;
    v_u_43.add_key_to_data = function(_, p158, p159) --[[ Name: add_key_to_data ]] --[[ Line: 568 ]]
        --[[ Upvalues: (copy 1): v_u_24, (ref 2): v_u_6 ]]
        if v_u_24:contains(p158) and v_u_24:get(p158).Loaded == p159.Loaded then
            v_u_6:errf("SongDatabase:add_key_to_data duplicate(%s)", (tostring(p158)))
        end;
        v_u_24:add(p158, p159)
        p159.__key = p158
    end;
    v_u_43.all_keys = function(_) --[[ Name: all_keys ]] --[[ Line: 579 ]]
        --[[ Upvalues: (copy 1): v_u_25 ]]
        return v_u_25;
    end;
    v_u_43.contains_key = function(_, p160) --[[ Name: contains_key ]] --[[ Line: 583 ]]
        --[[ Upvalues: (copy 1): v_u_24 ]]
        return v_u_24:contains(p160);
    end;
    v_u_43.key_to_name = function(_, p161) --[[ Name: key_to_name ]] --[[ Line: 587 ]]
        --[[ Upvalues: (ref 1): v_u_10 ]]
        return v_u_10[p161];
    end;
    v_u_43.key_has_combineinfo = function(_, p162) --[[ Name: key_has_combineinfo ]] --[[ Line: 589 ]]
        --[[ Upvalues: (copy 1): v_u_27 ]]
        if v_u_27:contains(p162) then
            return true, v_u_27:get(p162);
        else
            return false, nil;
        end;
    end;
    v_u_43.key_get_combine_result = function(p163, p164) --[[ Name: key_get_combine_result ]] --[[ Line: 597 ]]
        local v165, v166 = p163:key_has_combineinfo(p164)
        if v165 == true then
            return v166.OutputKey;
        else
            return nil;
        end;
    end;
    v_u_43.key_is_fusionresult_of = function(_, p167) --[[ Name: key_is_fusionresult_of ]] --[[ Line: 603 ]]
        --[[ Upvalues: (copy 1): v_u_28 ]]
        return v_u_28:get(p167);
    end;
    v_u_43.key_get_audiomod = function(_, p168) --[[ Name: key_get_audiomod ]] --[[ Line: 607 ]]
        --[[ Upvalues: (copy 1): v_u_24, (ref 2): v_u_7, (ref 3): v_u_3, (ref 4): v_u_20, (ref 5): v_u_19, (ref 6): v_u_9, (ref 7): v_u_8 ]]
        local v169 = v_u_24:get(p168)
        if v169 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
            v169.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p168 then
            v169.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v169 == nil then
            return v_u_19.MOD_NORMAL;
        else
            local l_AudioMod_0 = v169.AudioMod
            if v_u_9:test_enum_member(l_AudioMod_0, v_u_8) then
                return l_AudioMod_0;
            else
                return v_u_19.MOD_NORMAL;
            end;
        end;
    end;
    v_u_43.key_is_vip = function(_, p170) --[[ Name: key_is_vip ]] --[[ Line: 617 ]]
        --[[ Upvalues: (copy 1): v_u_24, (ref 2): v_u_7, (ref 3): v_u_3, (ref 4): v_u_20 ]]
        local v171 = v_u_24:get(p170)
        if v171 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
            v171.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p170 then
            v171.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v171 == nil then
            return false;
        else
            return v171.VIP == true;
        end;
    end;
    v_u_43.key_is_remix_flagged = function(_, p172) --[[ Name: key_is_remix_flagged ]] --[[ Line: 623 ]]
        --[[ Upvalues: (copy 1): v_u_24, (ref 2): v_u_7, (ref 3): v_u_3, (ref 4): v_u_20 ]]
        local v173 = v_u_24:get(p172)
        if v173 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
            v173.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p172 then
            v173.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v173 == nil then
            return false;
        else
            return v173.IsRemix == true;
        end;
    end;
    local v_u_174 = v_u_2:new():add_set_from_table_list({})
    v_u_43.render_coverimage_for_key = function(p175, p176, p177, p178) --[[ Name: render_coverimage_for_key ]] --[[ Line: 630 ]]
        --[[ Upvalues: (ref 1): v_u_19, (copy 2): v_u_174 ]]
        p176.Image = p175:get_coverimage_assetid_for_key(p178)
        local v179 = p175:key_get_audiomod(p178)
        if v179 == v_u_19.MOD_EASY then
            p177.Image = "rbxassetid://7335279699"
            p177.Visible = true
            return;
        elseif v179 == v_u_19.MOD_HARDMODE then
            if p175:key_is_vip(p178) == true and (p175:key_is_remix_flagged(p178) ~= true and v_u_174:contains(p178) ~= true) then
                p177.Image = "rbxassetid://11111112165"
            else
                p177.Image = "rbxassetid://837274453"
            end;
            p177.Visible = true
            return;
        elseif p175:key_is_vip(p178) == true and (p175:key_is_remix_flagged(p178) ~= true and v_u_174:contains(p178) ~= true) then
            p177.Image = "rbxassetid://11111112051"
            p177.Visible = true
        else
            p177.Visible = false
        end;
    end;
    v_u_43.get_coverimage_assetid_for_key = function(_, p180) --[[ Name: get_coverimage_assetid_for_key ]] --[[ Line: 654 ]]
        --[[ Upvalues: (copy 1): v_u_24, (ref 2): v_u_7, (ref 3): v_u_3, (ref 4): v_u_20 ]]
        local v181 = v_u_24:get(p180)
        if v181 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
            v181.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p180 then
            v181.AudioAssetId = v_u_20.AudioAssetId
        end;
        return v181 == nil and "" or v181.AudioCoverImageAssetId;
    end;
    v_u_43.get_title_for_key = function(_, p182) --[[ Name: get_title_for_key ]] --[[ Line: 662 ]]
        --[[ Upvalues: (copy 1): v_u_24, (ref 2): v_u_7, (ref 3): v_u_3, (ref 4): v_u_20 ]]
        local v183 = v_u_24:get(p182)
        if v183 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
            v183.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p182 then
            v183.AudioAssetId = v_u_20.AudioAssetId
        end;
        return v183 == nil and "" or v183.AudioFilename;
    end;
    local v_u_184 = v_u_2:new()
    v_u_43.get_title_lower_for_key = function(p185, p186) --[[ Name: get_title_lower_for_key ]] --[[ Line: 671 ]]
        --[[ Upvalues: (copy 1): v_u_184 ]]
        if v_u_184:contains(p186) ~= true then
            v_u_184:add(p186, (string.lower((p185:get_title_for_key(p186)))))
        end;
        return v_u_184:get(p186);
    end;
    v_u_43.get_artist_for_key = function(_, p187) --[[ Name: get_artist_for_key ]] --[[ Line: 680 ]]
        --[[ Upvalues: (copy 1): v_u_24, (ref 2): v_u_7, (ref 3): v_u_3, (ref 4): v_u_20 ]]
        local v188 = v_u_24:get(p187)
        if v188 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
            v188.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p187 then
            v188.AudioAssetId = v_u_20.AudioAssetId
        end;
        return v188 == nil and "" or v188.AudioArtist;
    end;
    local v_u_189 = v_u_2:new()
    v_u_43.get_artist_lower_for_key = function(p190, p191) --[[ Name: get_artist_lower_for_key ]] --[[ Line: 689 ]]
        --[[ Upvalues: (copy 1): v_u_189 ]]
        if v_u_189:contains(p191) ~= true then
            v_u_189:add(p191, (string.lower((p190:get_artist_for_key(p191)))))
        end;
        return v_u_189:get(p191);
    end;
    local v_u_192 = v_u_2:new()
    v_u_43.get_difficulty_for_key = function(_, p193) --[[ Name: get_difficulty_for_key ]] --[[ Line: 699 ]]
        --[[ Upvalues: (copy 1): v_u_192, (copy 2): v_u_24, (ref 3): v_u_7, (ref 4): v_u_3, (ref 5): v_u_20 ]]
        if v_u_192:contains(p193) ~= true then
            local v194 = v_u_24:get(p193)
            if v194 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
                v194.AudioAssetId = v_u_20.AudioAssetId
            end;
            if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p193 then
                v194.AudioAssetId = v_u_20.AudioAssetId
            end;
            if v194 == nil then
                return -1;
            end;
            v_u_192:add(p193, v194.AudioDifficulty)
        end;
        return v_u_192:get(p193);
    end;
    v_u_43.get_description_for_key = function(_, p195) --[[ Name: get_description_for_key ]] --[[ Line: 708 ]]
        --[[ Upvalues: (copy 1): v_u_24, (ref 2): v_u_7, (ref 3): v_u_3, (ref 4): v_u_20 ]]
        local v196 = v_u_24:get(p195)
        if v196 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
            v196.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p195 then
            v196.AudioAssetId = v_u_20.AudioAssetId
        end;
        return v196 == nil and "" or v196.AudioDescription;
    end;
    v_u_43.get_audio_assetid_for_key = function(_, p197) --[[ Name: get_audio_assetid_for_key ]] --[[ Line: 716 ]]
        --[[ Upvalues: (copy 1): v_u_24, (ref 2): v_u_7, (ref 3): v_u_3, (ref 4): v_u_20 ]]
        local v198 = v_u_24:get(p197)
        if v198 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
            v198.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p197 then
            v198.AudioAssetId = v_u_20.AudioAssetId
        end;
        return v198 == nil and "" or v198.AudioAssetId;
    end;
    v_u_43.get_audio_hitsfxgroup_for_key = function(_, p199) --[[ Name: get_audio_hitsfxgroup_for_key ]] --[[ Line: 725 ]]
        --[[ Upvalues: (copy 1): v_u_24, (ref 2): v_u_7, (ref 3): v_u_3, (ref 4): v_u_20 ]]
        local v200 = v_u_24:get(p199)
        if v200 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
            v200.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p199 then
            v200.AudioAssetId = v_u_20.AudioAssetId
        end;
        return v200 == nil and 0 or (v200.AudioHitSFXGroup == nil and 0 or v200.AudioHitSFXGroup);
    end;
    v_u_43.get_default_audio_volume = function(_) --[[ Name: get_default_audio_volume ]] --[[ Line: 733 ]]
        return 0.5;
    end;
    v_u_43.get_audio_volume_for_key = function(_, p201) --[[ Name: get_audio_volume_for_key ]] --[[ Line: 735 ]]
        --[[ Upvalues: (copy 1): v_u_24, (ref 2): v_u_7, (ref 3): v_u_3, (ref 4): v_u_20 ]]
        local v202 = v_u_24:get(p201)
        if v202 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
            v202.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p201 then
            v202.AudioAssetId = v_u_20.AudioAssetId
        end;
        return v202 == nil and 0.5 or (v202.AudioVolume == nil and 0.5 or v202.AudioVolume);
    end;
    v_u_43.get_audio_time_offset_for_key = function(_, p203) --[[ Name: get_audio_time_offset_for_key ]] --[[ Line: 742 ]]
        --[[ Upvalues: (copy 1): v_u_24, (ref 2): v_u_7, (ref 3): v_u_3, (ref 4): v_u_20 ]]
        local v204 = v_u_24:get(p203)
        if v204 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
            v204.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p203 then
            v204.AudioAssetId = v_u_20.AudioAssetId
        end;
        return v204 == nil and 0 or (v204.AudioTimeOffset == nil and 0 or v204.AudioTimeOffset);
    end;
    v_u_43.get_songdatabase_info = function(p205) --[[ Name: get_songdatabase_info ]] --[[ Line: 749 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_10, (ref 3): v_u_17 ]]
        local v206 = v_u_1:new()
        for v207 = 1, #v_u_10 do
            v206:push_back({
                ["songid"] = v207,
                ["songname"] = v_u_10[v207],
                ["audiomod"] = p205:key_get_audiomod(v207),
                ["difficulty"] = p205:get_difficulty_for_key(v207),
                ["audiocoverimg"] = p205:get_coverimage_assetid_for_key(v207),
                ["vip"] = p205:key_is_vip(v207),
                ["priority"] = p205:get_songkey_priority(v207),
                ["remix"] = p205:key_is_remix_flagged(v207),
                ["color1"] = v_u_17:songkey_primary_color(v207),
                ["color2"] = not v_u_17:songkey_has_secondary_color(v207) and -1 or v_u_17:songkey_secondary_color(v207)
            })
        end;
        return v206:get_table();
    end;
    v_u_43.songkey_get_prebuffer_time = function(_, p208) --[[ Name: songkey_get_prebuffer_time ]] --[[ Line: 773 ]]
        --[[ Upvalues: (copy 1): v_u_24, (ref 2): v_u_7, (ref 3): v_u_3, (ref 4): v_u_20 ]]
        local v209 = v_u_24:get(p208)
        if v209 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
            v209.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p208 then
            v209.AudioAssetId = v_u_20.AudioAssetId
        end;
        return v209.AudioNotePrebufferTime == nil and 1500 or v209.AudioNotePrebufferTime;
    end;
    v_u_43.songkey_get_approx_length_sec = function(_, p210) --[[ Name: songkey_get_approx_length_sec ]] --[[ Line: 782 ]]
        --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_24, (ref 3): v_u_3, (ref 4): v_u_20 ]]
        if v_u_7.SwapDebugSong == true then
            return 2.5;
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p210 then
            return 2.5;
        end;
        local v211 = v_u_24:get(p210)
        if v211 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
            v211.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p210 then
            v211.AudioAssetId = v_u_20.AudioAssetId
        end;
        return v211 == nil and 0 or (v211.LastNoteTime == nil and 0 or (v211.LastNoteTime + 1000) / 1000);
    end;
    v_u_43.songkey_get_average_bpm = function(_, p212) --[[ Name: songkey_get_average_bpm ]] --[[ Line: 794 ]]
        --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_24, (ref 3): v_u_3, (ref 4): v_u_20 ]]
        if v_u_7.SwapDebugSong == true then
            return -1;
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p212 then
            return 2.5;
        end;
        local v213 = v_u_24:get(p212)
        if v213 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
            v213.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p212 then
            v213.AudioAssetId = v_u_20.AudioAssetId
        end;
        return v213 == nil and -1 or (v213.BPM == nil and -1 or v213.BPM);
    end;
    v_u_43.get_difficulty_color_for_key = function(p214, p215) --[[ Name: get_difficulty_color_for_key ]] --[[ Line: 806 ]]
        return p214:get_difficulty_color_for_difficulty((p214:get_difficulty_for_key(p215)));
    end;
    v_u_43.get_difficulty_color_for_difficulty = function(_, p216) --[[ Name: get_difficulty_color_for_difficulty ]] --[[ Line: 811 ]]
        if p216 <= 5 then
            return Color3.fromRGB(121, 197, 21);
        elseif p216 <= 10 then
            return Color3.fromRGB(248, 204, 17);
        elseif p216 <= 15 then
            return Color3.fromRGB(228, 157, 16);
        elseif p216 <= 20 then
            return Color3.fromRGB(251, 125, 28);
        elseif p216 <= 25 then
            return Color3.fromRGB(242, 78, 21);
        else
            return Color3.fromRGB(215, 37, 36);
        end;
    end;
    v_u_43.get_songkey_hit_count = function(_, p217) --[[ Name: get_songkey_hit_count ]] --[[ Line: 827 ]]
        --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_20, (copy 3): v_u_24, (ref 4): v_u_3 ]]
        if v_u_7.SwapDebugSong == true then
            return v_u_20.HitCount;
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p217 then
            return v_u_20.HitCount;
        end;
        local v218 = v_u_24:get(p217)
        if v218 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
            v218.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p217 then
            v218.AudioAssetId = v_u_20.AudioAssetId
        end;
        return v218 == nil and 0 or (v218.HitCount == nil and 0 or v218.HitCount);
    end;
    v_u_43.get_songkey_hit_objects_count = function(_, p219) --[[ Name: get_songkey_hit_objects_count ]] --[[ Line: 840 ]]
        --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_20, (copy 3): v_u_24, (ref 4): v_u_3 ]]
        if v_u_7.SwapDebugSong == true then
            return v_u_20.HitObjectsCount;
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p219 then
            return v_u_20.HitObjectsCount;
        end;
        local v220 = v_u_24:get(p219)
        if v220 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
            v220.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p219 then
            v220.AudioAssetId = v_u_20.AudioAssetId
        end;
        return v220 == nil and 0 or (v220.HitObjectsCount == nil and 0 or v220.HitObjectsCount);
    end;
    v_u_43.get_easymode_keys_set = function(_) --[[ Name: get_easymode_keys_set ]] --[[ Line: 853 ]]
        --[[ Upvalues: (copy 1): v_u_29 ]]
        return v_u_29;
    end;
    v_u_43.get_easymode_crafting_normal_key_set = function(_) --[[ Name: get_easymode_crafting_normal_key_set ]] --[[ Line: 857 ]]
        --[[ Upvalues: (copy 1): v_u_30 ]]
        return v_u_30;
    end;
    v_u_43.get_songkey_to_easy_mode_dict = function(_) --[[ Name: get_songkey_to_easy_mode_dict ]] --[[ Line: 861 ]]
        --[[ Upvalues: (copy 1): v_u_31 ]]
        return v_u_31;
    end;
    v_u_43.get_easy_mode_to_songkey_dict = function(_) --[[ Name: get_easy_mode_to_songkey_dict ]] --[[ Line: 865 ]]
        --[[ Upvalues: (copy 1): v_u_32 ]]
        return v_u_32;
    end;
    v_u_43.get_songkey_priority = function(_, p221) --[[ Name: get_songkey_priority ]] --[[ Line: 869 ]]
        --[[ Upvalues: (copy 1): v_u_24, (ref 2): v_u_7, (ref 3): v_u_3, (ref 4): v_u_20, (ref 5): v_u_19 ]]
        local v222 = v_u_24:get(p221)
        if v222 and (v_u_7.SwapDebugSong == true and v_u_3:is_dev_build()) then
            v222.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v_u_7.SwapDebugSpecificSong == true and v_u_7.SwapDebugSpecificSongKey == p221 then
            v222.AudioAssetId = v_u_20.AudioAssetId
        end;
        if v222.Priority == nil then
            return v_u_19.SongPriority.Normal;
        else
            return v222.Priority;
        end;
    end;
    v_u_43.get_songkey_should_grant = function(p223, p224) --[[ Name: get_songkey_should_grant ]] --[[ Line: 875 ]]
        --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_19 ]]
        if p223:key_get_audiomod(p224) == v_u_8.Easy then
            return false;
        elseif p223:key_is_vip(p224) then
            return false;
        elseif p223:key_is_remix_flagged(p224) then
            return false;
        else
            return p223:get_songkey_priority(p224) ~= v_u_19.SongPriority.Hidden;
        end;
    end;
    local v_u_225 = nil
    local function _(p226, p227) --[[ Name: add_set_non_nil ]] --[[ Line: 892 ]]
        --[[ Upvalues: (ref 1): v_u_225 ]]
        if p227 ~= nil and p226:contains(p227) ~= true then
            p226:add_set(p227)
            v_u_225(p226, p227)
        end;
    end;
    v_u_225 = function(p228, p229) --[[ Line: 898 ]]
        --[[ Upvalues: (ref 1): v_u_225, (ref 2): v_u_19 ]]
        if p229 ~= nil and p228:contains(p229) ~= true then
            p228:add_set(p229)
            v_u_225(p228, p229)
        end;
        local v230 = v_u_19:singleton():key_get_combine_result(p229)
        if v230 ~= nil and p228:contains(v230) ~= true then
            p228:add_set(v230)
            v_u_225(p228, v230)
        end;
        local v231 = v_u_19:singleton():key_is_fusionresult_of(p229)
        if v231 ~= nil and p228:contains(v231) ~= true then
            p228:add_set(v231)
            v_u_225(p228, v231)
        end;
        local v232 = v_u_19:singleton():get_songkey_to_easy_mode_dict():get(p229)
        if v232 ~= nil and p228:contains(v232) ~= true then
            p228:add_set(v232)
            v_u_225(p228, v232)
        end;
        local v233 = v_u_19:singleton():get_easy_mode_to_songkey_dict():get(p229)
        if v233 ~= nil and p228:contains(v233) ~= true then
            p228:add_set(v233)
            v_u_225(p228, v233)
        end;
    end
    v_u_43.get_all_modes_of_songkey = function(_, p234) --[[ Name: get_all_modes_of_songkey ]] --[[ Line: 905 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_225 ]]
        local v235 = v_u_2:new()
        v_u_225(v235, p234)
        return v235;
    end;
    v_u_43.get_audiomod_to_modes_of_songkey = function(p236, p237) --[[ Name: get_audiomod_to_modes_of_songkey ]] --[[ Line: 910 ]]
        --[[ Upvalues: (ref 1): v_u_2 ]]
        local v238 = v_u_2:new()
        for v239, _ in p236:get_all_modes_of_songkey(p237):key_itr() do
            v238:add(p236:key_get_audiomod(v239), v239)
        end;
        return v238;
    end;
    v_u_43.count = function(_) --[[ Name: count ]] --[[ Line: 919 ]]
        --[[ Upvalues: (copy 1): v_u_25 ]]
        return v_u_25:count();
    end;
    f_cons()
    return v_u_43;
end;
local v_u_240 = v_u_19:new()
v_u_19.singleton = function(_) --[[ Name: singleton ]] --[[ Line: 926 ]]
    --[[ Upvalues: (copy 1): v_u_240 ]]
    return v_u_240;
end;
v_u_19.invalid_songkey = function(_) --[[ Name: invalid_songkey ]] --[[ Line: 930 ]]
    return -1;
end;
return v_u_19;
