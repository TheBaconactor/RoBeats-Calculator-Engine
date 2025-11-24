-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:28 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.GameSlot)
local v_u_1 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Local.AnimationManager)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Avatar.SPAvatarUtil)
require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
require(game.ReplicatedStorage.PlayerInfo.DanceType)
require(game.ReplicatedStorage.Shared.GameDanceInfo)
require(game.ReplicatedStorage.Shared.EventString)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
require(game.ReplicatedStorage.Shared.MatchMode)
require(game.ReplicatedStorage.Effects.CharacterShineEffect)
local v_u_8 = require(game.ReplicatedStorage.Pets.PetDatabase)
local v_u_9 = require(game.ReplicatedStorage.Pets.PetUtils)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.GenericArtistEventInfo)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.GenericArtistP2EventInfo)
local v_u_13 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.GenericArtistP3EventInfo)
require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_14 = require(game.ReplicatedStorage.Shared.NoCollideGroup)
local v15 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_16 = nil
v15:require_shared(function() --[[ Line: 30 ]]
    --[[ Upvalues: (ref 1): v_u_16 ]]
    v_u_16 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.Black17EventInfo)
end)
local v_u_49 = {
    ["Tag"] = {
        ["EventBackupDancer"] = 0,
        ["PetSlot1"] = 1,
        ["PetSlot2"] = 2,
        ["PetSlot3"] = 3
    },
    ["new"] = function(_, _, p_u_17) --[[ Name: new ]] --[[ Line: 41 ]]
        --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_3, (copy 3): v_u_1, (copy 4): v_u_2 ]]
        local v18 = {}
        local v_u_19 = nil
        local v_u_20 = nil
        local v_u_21 = nil
        local v_u_22 = v_u_6:new()
        local v_u_23 = v_u_3:new()
        local function _() --[[ Name: is_initialized ]] --[[ Line: 51 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_21, (copy 3): v_u_23 ]]
            local v24 = v_u_20 and v_u_21
            if v24 then
                v24 = v_u_23:count() == 0
            end;
            return v24;
        end;
        local function _(p25) --[[ Name: on_set_character ]] --[[ Line: 55 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_21, (copy 3): v_u_23 ]]
            local v26 = v_u_20 and v_u_21
            if v26 then
                v26 = v_u_23:count() == 0
            end;
            if v26 then
                p25()
            else
                v_u_23:push_back(p25)
            end;
        end;
        v18.set_character = function(_, p27) --[[ Name: set_character ]] --[[ Line: 64 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_20, (ref 3): v_u_21, (ref 4): v_u_1, (copy 5): v_u_23 ]]
            v_u_19 = p27
            pcall(function() --[[ Line: 66 ]]
                --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_19, (ref 3): v_u_21 ]]
                v_u_20 = v_u_19.Humanoid
                v_u_21 = v_u_19.PrimaryPart
            end)
            if v_u_20 == nil or v_u_21 == nil then
                return v_u_1:warnf("BackupDancer:set_character failed to initialize _humanoid(%s) _primary_part(%s)", tostring(v_u_20), (tostring(v_u_21)));
            end;
            for _, v28 in v_u_23:key_itr() do
                v28()
            end;
            v_u_23:clear()
        end;
        v18.get_tag = function(_) --[[ Name: get_tag ]] --[[ Line: 79 ]]
            --[[ Upvalues: (copy 1): p_u_17 ]]
            return p_u_17;
        end;
        local v_u_29 = Vector3.new()
        v18.set_position_offset = function(_, p30) --[[ Name: set_position_offset ]] --[[ Line: 82 ]]
            --[[ Upvalues: (ref 1): v_u_29 ]]
            v_u_29 = p30
        end;
        v18.get_position_offset = function(_) --[[ Name: get_position_offset ]] --[[ Line: 83 ]]
            --[[ Upvalues: (ref 1): v_u_29 ]]
            return v_u_29;
        end;
        v18.preload_dance_type_animation = function(_, _, p_u_31) --[[ Name: preload_dance_type_animation ]] --[[ Line: 85 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_2, (copy 3): v_u_22, (ref 4): v_u_21, (copy 5): v_u_23 ]]
            local function v32() --[[ Line: 86 ]]
                --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_2, (ref 3): v_u_22, (copy 4): p_u_31 ]]
                if v_u_20 ~= nil then
                    v_u_2:ptry(function() --[[ Line: 88 ]]
                        --[[ Upvalues: (ref 1): v_u_22, (ref 2): p_u_31, (ref 3): v_u_20 ]]
                        v_u_22:add(p_u_31, v_u_20:LoadAnimation(p_u_31))
                    end)
                end;
            end;
            local v33 = v_u_20 and v_u_21
            if v33 then
                v33 = v_u_23:count() == 0
            end;
            if v33 then
                v32()
            else
                v_u_23:push_back(v32)
            end;
        end;
        local v_u_34 = nil
        local function _(p35) --[[ Name: do_play_animation_assetid ]] --[[ Line: 95 ]]
            --[[ Upvalues: (copy 1): v_u_22, (ref 2): v_u_34 ]]
            if v_u_22:contains(p35) then
                if v_u_34 then
                    v_u_34:Stop()
                end;
                v_u_34 = v_u_22:get(p35)
                v_u_34:Play()
            end;
        end;
        v18.play_animation_assetid = function(_, p_u_36) --[[ Name: play_animation_assetid ]] --[[ Line: 105 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_21, (copy 3): v_u_23, (copy 4): v_u_22, (ref 5): v_u_34 ]]
            local v37 = v_u_20 and v_u_21
            if v37 then
                v37 = v_u_23:count() == 0
            end;
            if v37 then
                if v_u_22:contains(p_u_36) then
                    if v_u_34 then
                        v_u_34:Stop()
                    end;
                    v_u_34 = v_u_22:get(p_u_36)
                    v_u_34:Play()
                    return;
                end;
            else
                local function v39() --[[ Line: 109 ]]
                    --[[ Upvalues: (copy 1): p_u_36, (ref 2): v_u_22, (ref 3): v_u_34 ]]
                    local v38 = p_u_36
                    if v_u_22:contains(v38) then
                        if v_u_34 then
                            v_u_34:Stop()
                        end;
                        v_u_34 = v_u_22:get(v38)
                        v_u_34:Play()
                    end;
                end;
                local v40 = v_u_20 and v_u_21
                if v40 then
                    v40 = v_u_23:count() == 0
                end;
                if v40 then
                    v39()
                    return;
                end;
                v_u_23:push_back(v39)
            end;
        end;
        v18.set_anchored = function(_, p_u_41) --[[ Name: set_anchored ]] --[[ Line: 115 ]]
            --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_20, (copy 3): v_u_23 ]]
            local function v42() --[[ Line: 116 ]]
                --[[ Upvalues: (ref 1): v_u_21, (copy 2): p_u_41 ]]
                if v_u_21 then
                    v_u_21.Anchored = p_u_41
                end;
            end;
            local v43 = v_u_20 and v_u_21
            if v43 then
                v43 = v_u_23:count() == 0
            end;
            if v43 then
                v42()
            else
                v_u_23:push_back(v42)
            end;
        end;
        v18.set_cframe = function(_, p_u_44) --[[ Name: set_cframe ]] --[[ Line: 123 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_20, (ref 3): v_u_21, (copy 4): v_u_23 ]]
            local function v45() --[[ Line: 124 ]]
                --[[ Upvalues: (ref 1): v_u_19, (copy 2): p_u_44 ]]
                if v_u_19 then
                    v_u_19:SetPrimaryPartCFrame(p_u_44)
                end;
            end;
            local v46 = v_u_20 and v_u_21
            if v46 then
                v46 = v_u_23:count() == 0
            end;
            if v46 then
                v45()
            else
                v_u_23:push_back(v45)
            end;
        end;
        v18.cleanup = function(_) --[[ Name: cleanup ]] --[[ Line: 131 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_20, (ref 3): v_u_21, (copy 4): v_u_23 ]]
            local function v47() --[[ Line: 132 ]]
                --[[ Upvalues: (ref 1): v_u_19 ]]
                if v_u_19 then
                    v_u_19:Destroy()
                end;
            end;
            local v48 = v_u_20 and v_u_21
            if v48 then
                v48 = v_u_23:count() == 0
            end;
            if v48 then
                v47()
            else
                v_u_23:push_back(v47)
            end;
        end;
        return v18;
    end
}
v_u_49.create_backup_dancers = function(_, p50, p51, p52) --[[ Name: create_backup_dancers ]] --[[ Line: 142 ]]
    --[[ Upvalues: (copy 1): v_u_49, (copy 2): v_u_5, (copy 3): v_u_9, (copy 4): v_u_8, (copy 5): v_u_4 ]]
    v_u_49:create_event_backup_dancers(p50, p51, p52)
    if v_u_5.DebugMinisActive == true then
        local function _(p53) --[[ Name: pet_slot_to_tag ]] --[[ Line: 146 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_49 ]]
            if p53 == v_u_9:get_pet_slot_1_id() then
                return v_u_49.Tag.PetSlot1;
            elseif p53 == v_u_9:get_pet_slot_2_id() then
                return v_u_49.Tag.PetSlot2;
            else
                return v_u_49.Tag.PetSlot3;
            end;
        end;
        for v54, v55 in v_u_9:displaypet_table_get_slot_to_petid_dict(p52._display_pet_tab):key_itr() do
            local v56 = v_u_8:singleton():get_data_for_petid(v55)
            if not v56 then
                return;
            end;
            local v57 = v_u_49
            local v58
            if v54 == v_u_9:get_pet_slot_1_id() then
                v58 = v_u_49.Tag.PetSlot1
            elseif v54 == v_u_9:get_pet_slot_2_id() then
                v58 = v_u_49.Tag.PetSlot2
            else
                v58 = v_u_49.Tag.PetSlot3
            end;
            local v_u_59 = v57:new(p50, v58)
            p51:get_backup_dancers():push_back(v_u_59)
            v56:create_character(v_u_8.DEFAULT_CREATE_PET_PARAMS, v_u_4:get_local_elements_folder(), function(p_u_60) --[[ Line: 167 ]]
                --[[ Upvalues: (copy 1): v_u_59 ]]
                v_u_59:set_character(p_u_60)
                pcall(function() --[[ Line: 169 ]]
                    --[[ Upvalues: (copy 1): p_u_60 ]]
                    p_u_60.PrimaryPart.Anchored = true
                end)
            end)
        end;
    end;
end;
local v_u_61 = v_u_6:new():add_set_from_table_list({ v_u_49.Tag.PetSlot1, v_u_49.Tag.PetSlot2, v_u_49.Tag.PetSlot3 })
v_u_49.set_backup_dancer_positions = function(_, p_u_62, p63) --[[ Name: set_backup_dancer_positions ]] --[[ Line: 184 ]]
    --[[ Upvalues: (copy 1): v_u_61, (copy 2): v_u_49 ]]
    local v_u_64, _, v_u_65, v_u_66, v67 = p63:get_character_location()
    local function _() --[[ Name: get_dancer_across_position ]] --[[ Line: 186 ]]
        --[[ Upvalues: (copy 1): p_u_62, (copy 2): v_u_64, (copy 3): v_u_66, (copy 4): v_u_65 ]]
        if p_u_62:show_fullscreen_mobile_ui() then
            return v_u_64 + v_u_66 * -25 + v_u_65 * 0;
        else
            return v_u_64 + v_u_66 * -22.5 + v_u_65 * 0;
        end;
    end;
    for _, v68 in p63:get_backup_dancers():key_itr() do
        local v69 = CFrame.new()
        if v_u_61:contains(v68:get_tag()) then
            if v68:get_tag() == v_u_49.Tag.PetSlot1 then
                v69 = v_u_64 + v_u_66 * 3.5 + v_u_65 * 0
            elseif v68:get_tag() == v_u_49.Tag.PetSlot2 then
                v69 = v_u_64 + v_u_66 * -3.5 + v_u_65 * 0
            elseif v68:get_tag() == v_u_49.Tag.PetSlot3 then
                v69 = v_u_64 + v_u_66 * 0 + v_u_65 * -3.5 * 1.5
            end;
            v69 = v69 + v67 * -2.25 + v_u_65 * -1.25
        elseif v68:get_tag() == v_u_49.Tag.EventBackupDancer then
            if p_u_62:show_fullscreen_mobile_ui() then
                v69 = v_u_64 + v_u_66 * -25 + v_u_65 * 0
            else
                v69 = v_u_64 + v_u_66 * -22.5 + v_u_65 * 0
            end;
            p_u_62._world_effect_manager:game_create_shine_for_slot_at_cframe(p_u_62, p63:get_game_slot(), v69)
        end;
        v68:set_cframe(v69 + v68:get_position_offset())
    end;
end;
v_u_49.create_event_backup_dancers = function(_, p70, p71, _) --[[ Name: create_event_backup_dancers ]] --[[ Line: 229 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_7, (copy 3): v_u_11, (copy 4): v_u_12, (copy 5): v_u_13, (copy 6): v_u_10, (ref 7): v_u_16, (copy 8): v_u_49, (copy 9): v_u_4, (copy 10): v_u_2, (copy 11): v_u_14 ]]
    if p70:is_spectate() or p71:get_slot() == p70:get_local_game_slot() then
        if p70:is_preview_game() ~= true then
            local v72 = p70:es_gamelocal_get_audiomanager():get_song_key()
            local v73 = Vector3.new()
            local v74 = v_u_3:new()
            local v75, v76 = v_u_7:is_event_active(p70._player_blob_manager:get_day_event_list())
            if v_u_11:is_event_active(p70._player_blob_manager:get_day_event_list()) == true and (v_u_11:get_playable_song_set():contains(v72) and v_u_11:get_backup_dancer_npc_id() ~= nil) then
                v74:push_back(v_u_11:get_backup_dancer_npc_id())
            elseif v_u_12:is_event_active(p70._player_blob_manager:get_day_event_list()) == true and (v_u_12:get_playable_song_set():contains(v72) and v_u_11:get_backup_dancer_npc_id() ~= nil) then
                v74:push_back(v_u_12:get_backup_dancer_npc_id())
            elseif v_u_13:is_event_active(p70._player_blob_manager:get_day_event_list()) == true and (v_u_13:get_playable_song_set():contains(v72) and v_u_11:get_backup_dancer_npc_id() ~= nil) then
                v74:push_back(v_u_13:get_backup_dancer_npc_id())
            elseif p70:get_event_info() == v_u_10.EventMission.Black17Event and v_u_16:get_all_songkeys_set():contains(v72) then
                v74:push_back(v_u_16:get_backup_dancer_npc_id())
            elseif v75 and (p70:get_event_info() == v_u_10.EventMission.ArtistEvent and v_u_11:get_playable_song_set():contains(v72) ~= true) then
                local v77 = v_u_7:get_event_info(v76)
                if v77 and v77:get_songs_set():contains(v72) then
                    local v78 = v_u_7:get_event_info(v76):get_lobby_npc_info()
                    v74 = v_u_3:new(typeof(v78) ~= "table" and { v78 } or v78)
                end;
            end;
            if v74:count() > 0 then
                local v79 = v74:random()
                local v_u_80 = v_u_49:new(p70, v_u_49.Tag.EventBackupDancer)
                v_u_4:load_db_npc_character_and_humanoid(v79, true, function(p81, _) --[[ Line: 270 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_14, (ref 3): v_u_4, (copy 4): v_u_80 ]]
                    for _, v82 in pairs(p81:GetChildren()) do
                        if v_u_2:obj_has_children_of_names(v82, { v_u_14.MoveToEnvironment }) or (v_u_2:obj_has_children_of_names(v82, { v_u_14.DoCollide }) or v_u_2:obj_has_children_of_names(v82, { v_u_14.MoveToEnvironmentNoPopper })) then
                            v82:Destroy()
                        end;
                        p81.Parent = v_u_4:get_local_elements_folder()
                    end;
                    v_u_80:set_character(p81)
                end)
                v_u_80:set_position_offset(v73)
                p71:get_backup_dancers():push_back(v_u_80)
            end;
        end;
    else
        return;
    end;
end;
return v_u_49;
