-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:37 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Lobby.NPC.NPCBase)
local v_u_2 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v3 = require(game.ReplicatedStorage.Local.AnimationManager)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Lobby.NPCPopup)
require(game.ReplicatedStorage.Lobby.NPCPopupDialogue)
local v_u_7 = require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Menu.CharacterDialogue)
local v_u_8 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
require(game.ReplicatedStorage.PlayerInfo.WebNPCPurchaseInfo)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v9 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Lobby.NPC.WebNPC)
local v_u_10 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_11 = require(game.ReplicatedStorage.Shared.PlayerStatus)
local v_u_12 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_13 = require(game.ReplicatedStorage.LocalShared.CharacterCloneCache)
local v_u_14 = require(game.ReplicatedStorage.LocalShared.CharacterCulling)
local v15 = {}
local v_u_16 = v9:new():push_back_table_list({
    v3.ANIM_TANTRUM,
    v3.ANIM_DIZZYFALL,
    v3.ANIM_SIGH,
    v3.ANIM_SWAY,
    v3.ANIM_SPINPOSE,
    v3.ANIM_FOURSTEPSWAY,
    v3.ANIM_WAVE,
    v3.ANIM_OLDSCHOOLSHUFFLE,
    v3.ANIM_HIPHOPSWAY,
    v3.ANIM_IDLE,
    v3.ANIM_BREAKDANCE,
    v3.ANIM_BREAKDANCESPIN,
    v3.ANIM_DANCEROYALE
})
v15.new = function(_, p_u_17, p_u_18, p_u_19) --[[ Name: new ]] --[[ Line: 40 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_13, (copy 3): v_u_12, (copy 4): v_u_4, (copy 5): v_u_7, (copy 6): v_u_2, (copy 7): v_u_10, (copy 8): v_u_16, (copy 9): v_u_6, (copy 10): v_u_8, (copy 11): v_u_11, (copy 12): v_u_5, (copy 13): v_u_14 ]]
    local v_u_20 = v_u_1:new(p_u_17, p_u_18)
    local v_u_21 = string.format("MatchPreviewNPC_%d", p_u_19:get_player_id())
    local v_u_22 = nil
    local v_u_23 = nil
    local v_u_24 = 0
    local function f_cons() --[[ Name: cons ]] --[[ Line: 52 ]]
        --[[ Upvalues: (ref 1): v_u_24, (copy 2): p_u_19, (ref 3): v_u_23, (ref 4): v_u_13, (ref 5): v_u_12, (ref 6): v_u_4, (ref 7): v_u_7, (copy 8): v_u_21, (ref 9): v_u_2, (ref 10): v_u_22, (copy 11): p_u_17, (ref 12): v_u_10, (copy 13): v_u_20, (ref 14): v_u_16 ]]
        v_u_24 = p_u_19:get_playback_time_sec()
        v_u_23 = v_u_13:get_cached_match_preview_npc_for_userid(p_u_19:get_player_id())
        if v_u_23 == nil or v_u_12.ReuseMatchPreviewNPC ~= true then
            if v_u_4:is_dev_build() then
                v_u_7:puts("creating new MatchPreviewNPC obj for player(%d)", p_u_19:get_player_id())
            end;
            local l_Character_0 = game.ReplicatedStorage.LobbyElementProtos.MatchPreviewNPC.Character
            local l_MatchPreviewPlatform_0 = game.ReplicatedStorage.LobbyElementProtos.MatchPreviewNPC.MatchPreviewPlatform
            v_u_23 = Instance.new("Model")
            v_u_23.Name = v_u_21
            local v25 = v_u_2:get_character_model_for_playerid(p_u_19:get_player_id())
            if v25 == nil then
                v_u_7:warnf("MatchPreviewNPC(%d) character model not found, using default", p_u_19:get_player_id())
                v_u_22 = l_Character_0:Clone()
            end;
            v25.Archivable = true
            v_u_22 = v25:Clone()
            v25.Archivable = false
            v_u_22.Name = "MatchPreviewNPC"
            v_u_22.Humanoid.RootPart.Anchored = true
            v_u_4:r_set_basepart_fn(v_u_22, function(p26) --[[ Line: 78 ]]
                --[[ Upvalues: (ref 1): v_u_2, (ref 2): p_u_17 ]]
                p26:SetAttribute(v_u_2:get_no_trigger_dance_sync_attribute_name(), true)
                p26.CollisionGroupId = p_u_17:get_character_group_id()
            end)
            v_u_22:SetPrimaryPartCFrame(l_Character_0.PrimaryPart.CFrame)
            local v27 = l_MatchPreviewPlatform_0:Clone()
            v27.Name = "Platform"
            v27.Anchored = true
            v27.Parent = v_u_23
            v27.CFrame = l_MatchPreviewPlatform_0.CFrame
            v_u_22.Parent = v_u_23
            v_u_23.PrimaryPart = v_u_22.PrimaryPart
            v_u_23:SetPrimaryPartCFrame(p_u_19:get_cframe())
            v_u_23.Parent = v_u_2:get_npc_root()
            local v28 = v_u_4:first_child_of_type(l_Character_0, "Humanoid")
            local v29 = v_u_4:first_child_of_type(v_u_22, "Humanoid")
            if v28 and v29 then
                local v30 = v28:GetAppliedDescription()
                local v31 = v29:GetAppliedDescription()
                v31.DepthScale = v30.DepthScale
                v31.HeadScale = v30.HeadScale
                v31.HeightScale = v30.HeightScale
                v31.ProportionScale = v30.ProportionScale
                v31.WidthScale = v30.WidthScale
                v29:ApplyDescription(v31)
            end;
        elseif v_u_4:is_dev_build() then
            v_u_7:puts("using cached MatchPreviewNPC obj for player(%d)", p_u_19:get_player_id())
        end;
        local v32, v33 = pcall(function() --[[ Line: 119 ]]
            --[[ Upvalues: (ref 1): v_u_23, (ref 2): p_u_19, (ref 3): v_u_22, (ref 4): v_u_10, (ref 5): v_u_2 ]]
            v_u_23:SetPrimaryPartCFrame(p_u_19:get_cframe())
            v_u_22 = v_u_23.MatchPreviewNPC
            local l_SurfaceGui_0 = v_u_23.Platform.Part.SurfaceGui
            if p_u_19:get_songkey() ~= v_u_10:invalid_songkey() then
                l_SurfaceGui_0.SongDifficultySection.Display.Text = tostring(v_u_10:singleton():get_difficulty_for_key(p_u_19:get_songkey()))
                l_SurfaceGui_0.SongDifficultySection.Display.TextColor3 = v_u_10:singleton():get_difficulty_color_for_key(p_u_19:get_songkey())
                v_u_10:singleton():render_coverimage_for_key(l_SurfaceGui_0.Icon, l_SurfaceGui_0.IconOverlay, p_u_19:get_songkey())
            end;
            v_u_23.Parent = v_u_2:get_npc_root()
        end)
        if not v32 then
            v_u_7:errf("MatchPreviewNPC(%d) failed to load: %s", p_u_19:get_player_id(), v33)
        end;
        v_u_20:play_anim(v_u_20:load_anim(v_u_22.Humanoid, v_u_16:random()))
    end;
    v_u_20.get_popup_proto = function(_) --[[ Name: get_popup_proto ]] --[[ Line: 139 ]]
        return game.ReplicatedStorage.LobbyElementProtos.CharacterOverlay.DialoguePopupSpectate;
    end;
    v_u_20.on_popup_triggered = function(_) --[[ Name: on_popup_triggered ]] --[[ Line: 140 ]]
        --[[ Upvalues: (copy 1): p_u_18, (copy 2): p_u_17, (ref 3): v_u_6, (ref 4): v_u_8, (copy 5): p_u_19 ]]
        local l__menus_0 = p_u_18._menus
        local l__spui_0 = p_u_18._spui
        p_u_17._sfx_manager:play_sfx(v_u_6.SFX_MENU_OPEN)
        local v_u_34 = l__menus_0:push_menu(v_u_8:new(p_u_17, l__spui_0, l__menus_0):set_text("Joining Match...", "Please wait..."):set_close_button_visible(false))
        p_u_17._spectate_manager:try_spectate_userid(p_u_19:get_player_id(), function(p35, p36, p37) --[[ Line: 145 ]]
            --[[ Upvalues: (copy 1): l__menus_0, (copy 2): v_u_34, (ref 3): v_u_8, (ref 4): p_u_17, (copy 5): l__spui_0 ]]
            l__menus_0:remove_menu(v_u_34)
            if p35 ~= true then
                l__menus_0:push_menu(v_u_8:new(p_u_17, l__spui_0, l__menus_0):set_text("Error", p36))
            end;
            p37()
        end)
    end;
    local v_u_38 = ""
    v_u_20.update = function(p39, p40) --[[ Name: update ]] --[[ Line: 155 ]]
        --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_19, (copy 3): p_u_18, (ref 4): v_u_11, (ref 5): v_u_24, (ref 6): v_u_10, (ref 7): v_u_38, (ref 8): v_u_5 ]]
        p39:update_base(p40)
        v_u_4:profilebegin("MatchPreviewNPC:update")
        if v_u_4:distance_to_camera(p_u_19:get_cframe().p) < 50 then
            local v41 = p39:get_nametag()
            local v42 = p39:get_popup()
            local v43 = v41 and v42 and v41:get_description_display()
            if v43 then
                local v44 = p_u_18._player_status_manager:get_status_for_id(p_u_19:get_player_id()):get_mode()
                local v45 = ""
                if v44 == v_u_11.Mode.MatchPlaying then
                    v45 = string.format("%s / %s", v_u_4:format_ms_time(v_u_24 * 1000), v_u_4:format_ms_time(v_u_10:singleton():songkey_get_approx_length_sec(p_u_19:get_songkey()) * 1000))
                    v42:set_enabled(true)
                elseif v44 == v_u_11.Mode.MatchFinished then
                    v42:set_enabled(false)
                    v45 = "Match Finished"
                elseif v44 == v_u_11.Mode.InSettings then
                    v42:set_enabled(false)
                    v45 = "In Settings"
                end;
                if v45 ~= v_u_38 then
                    v43.Text = v45
                    v_u_38 = v45
                end;
            end;
        end;
        v_u_24 = v_u_5:IncrementClamp(v_u_24, v_u_5:TimescaleToDeltaTime(p40), 0, v_u_10:singleton():songkey_get_approx_length_sec(p_u_19:get_songkey()))
        v_u_4:profileend()
    end;
    v_u_20.cleanup = function(p46) --[[ Name: cleanup ]] --[[ Line: 201 ]]
        --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_14, (ref 3): v_u_23, (ref 4): v_u_4, (ref 5): v_u_7, (copy 6): p_u_18, (copy 7): p_u_19, (ref 8): v_u_13, (ref 9): v_u_22 ]]
        p46:cleanup_nametag_and_popup()
        if v_u_12.ReuseMatchPreviewNPC then
            local v47 = p46:get_current_anim_track()
            if v47 then
                v47:Stop()
            end;
            if v_u_4:is_dev_build() and v_u_14:remove_managed_character(v_u_23) ~= true then
                v_u_7:warnf("MatchPreviewNPC(%s) failed to remove CharacterCulling managed character", v_u_23:GetFullName())
            end;
            if p_u_18._lobby_join:get_character_manager():get_id_to_playerinfo():contains(p_u_19:get_player_id()) then
                v_u_13:cache_match_preview_npc_for_userid(p_u_19:get_player_id(), v_u_23)
            else
                v_u_23:Destroy()
            end;
            v_u_23 = nil
            v_u_22 = nil
        else
            v_u_23:Destroy()
        end;
    end;
    v_u_20.get_id = function(_) --[[ Name: get_id ]] --[[ Line: 226 ]]
        --[[ Upvalues: (copy 1): v_u_21 ]]
        return v_u_21;
    end;
    v_u_20.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 230 ]]
        --[[ Upvalues: (copy 1): p_u_19 ]]
        return p_u_19:get_player_name();
    end;
    v_u_20.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 231 ]]
        return "";
    end;
    v_u_20.get_nametag_position_offset = function(_) --[[ Name: get_nametag_position_offset ]] --[[ Line: 232 ]]
        return Vector3.new(0, 2, 0);
    end;
    v_u_20.get_root = function(_) --[[ Name: get_root ]] --[[ Line: 234 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        return v_u_22;
    end;
    f_cons()
    return v_u_20;
end;
return v15;
