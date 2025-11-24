-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:45 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.AudioData.AudioMod)
local v_u_4 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
return {
    ["scan_audiodata_for_errors"] = function(_, p6, p7) --[[ Name: scan_audiodata_for_errors ]] --[[ Line: 9 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4, (copy 3): v_u_2, (copy 4): v_u_5, (copy 5): v_u_3 ]]
        local v8 = v_u_1:new()
        v8:add(1, -100)
        v8:add(2, -100)
        v8:add(3, -100)
        v8:add(4, -100)
        local v9 = v8:get(1)
        for v10 = 1, #p7.HitObjects do
            local l_HitObjects_0 = p7.HitObjects[v10]
            local l_Time_0 = l_HitObjects_0.Time
            v_u_4:is_true(v9 <= l_Time_0)
            local l_Track_0 = l_HitObjects_0.Track
            v_u_4:is_non_nil(l_Time_0)
            v_u_4:is_non_nil(l_Track_0)
            if l_Time_0 <= v8:get(l_Track_0) + 25 then
                v_u_2:errf("SongErrorParser - Likely duplicate time/track note for (%s) at note[%d](Type[%d] Time[%d] Track[%d]) last_time(%d)", p7.AudioFilename, v10, l_HitObjects_0.Type, l_HitObjects_0.Time, l_Track_0, v8:get(l_Track_0))
            end;
            if l_HitObjects_0.Type == 2 then
                v8:add(l_Track_0, l_Time_0 + l_HitObjects_0.Duration)
                v9 = l_Time_0
            else
                v8:add(l_Track_0, l_Time_0)
                v9 = l_Time_0
            end;
        end;
        if p7.AudioAssetId == nil or (p7.AudioCoverImageAssetId == nil or (p7.AudioDescription == nil or (p7.AudioTimeOffset == nil or (p7.AudioArtist == nil or (p7.AudioFilename == nil or (p7.AudioDifficulty == nil or p7.AudioMod == nil)))))) then
            v_u_2:errf("SongErrorParser(%s) param is nil %s", tostring(p6), v_u_5:table_to_string(p7))
        end;
        if v_u_4:test_enum_member(p7.AudioMod, v_u_3) ~= true then
            v_u_2:errf("SongErrorParser - invalid AudioMod(%s) for (%s)", tostring(p7.AudioMod), (tostring(p7.AudioFilename)))
        end;
        if p7.AudioMod == v_u_3.Normal then
            if p7.FusionResult ~= nil and string.find(p7.FusionResult, "2") == nil then
                v_u_2:errf("SongErrorParser - invalid FusionResult(%s)", (tostring(p7.FusionResult)))
            end;
        elseif p7.AudioMod == v_u_3.Easy then
            if p7.FusionResult ~= nil and string.find(p7.FusionResult, "1") == nil then
                v_u_2:errf("SongErrorParser - invalid FusionResult(%s)", (tostring(p7.FusionResult)))
            end;
        elseif p7.AudioMod == v_u_3.Hard and (p7.FusionResult ~= nil and #p7.FusionResult > 0) then
            v_u_2:errf("SongErrorParser - file(%s) audiomod(%s) has fusionresult(%s)", tostring(p7.AudioFilename), tostring(p7.AudioMod), (tostring(p7.FusionResult)))
        end;
        if p7.AudioMod == v_u_3.Hard and string.find(p7.AudioFilename, "(Hard)") == nil then
            v_u_2:errf("SongErrorParser - Key(%s) AudioFilename(%s) missing (\"Hard\")", p6, p7.AudioFilename)
        end;
        if p7.AudioDifficulty > 50 then
            v_u_2:errf("SongErrorParser - invalid AudioDifficulty(%s)", (tostring(p7.AudioDifficulty)))
        end;
        if #p7.AudioAssetId == 0 or (#p7.AudioFilename == 0 or (#p7.AudioArtist == 0 or #p7.AudioCoverImageAssetId == 0)) then
            v_u_2:errf("SongErrorParser - zerolen str for (%s)", p7.AudioFilename)
        end;
    end
};
