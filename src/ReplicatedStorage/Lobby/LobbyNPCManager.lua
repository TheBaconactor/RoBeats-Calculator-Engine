-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:34 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_6 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Lobby.NPC.NPCBase)
local v_u_7 = require(game.ReplicatedStorage.Lobby.WebNPCManager)
require(game.ReplicatedStorage.Shared.Constants)
require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
require(game.ReplicatedStorage.PlayerInfo.DayEventInfo)
require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Local.AnimationManager)
local v_u_8 = require(game.ReplicatedStorage.Lobby.MatchPreviewNPCManager)
local v_u_9 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
local v_u_10 = require(game.ReplicatedStorage.Lobby.Menus.ArtistEventUI)
local v_u_11 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.TitleDatabase)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_13 = require(game.ReplicatedStorage.LocalShared.FrameIndex)
local s_MarketplaceService_0 = game:GetService("MarketplaceService")
local v_u_14 = require(game.ReplicatedStorage.Lobby.NPC.NPCStarMachine)
local v_u_15 = require(game.ReplicatedStorage.Lobby.NPC.NPCRobuxShopRoxie)
local v_u_16 = require(game.ReplicatedStorage.Lobby.NPC.NPCSongShopMarie)
local v_u_17 = require(game.ReplicatedStorage.Lobby.NPC.NPCSongShopMattie)
local v_u_18 = require(game.ReplicatedStorage.Lobby.NPC.NPCSpotco)
local v_u_19 = require(game.ReplicatedStorage.Lobby.NPC.NPCStarlet)
local v_u_20 = require(game.ReplicatedStorage.Lobby.NPC.NPCZara)
local v_u_21 = require(game.ReplicatedStorage.Lobby.NPC.NPCSputil)
local v_u_22 = require(game.ReplicatedStorage.Lobby.NPC.NPCNoteMachine)
local v_u_23 = require(game.ReplicatedStorage.Lobby.NPC.NPCLisa)
local v_u_24 = require(game.ReplicatedStorage.Lobby.NPC.NPCDJ)
local v_u_25 = require(game.ReplicatedStorage.Lobby.NPC.NPCDanceMachine)
local v_u_26 = require(game.ReplicatedStorage.Lobby.NPC.NPCMarketplace)
local v_u_27 = require(game.ReplicatedStorage.Lobby.NPC.NPCGuild)
local v_u_28 = require(game.ReplicatedStorage.Lobby.NPC.NPCEditor)
local v_u_29 = require(game.ReplicatedStorage.Lobby.NPC.NPCDialogPrompt)
local v30 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_31 = nil
local v_u_32 = nil
local v_u_33 = nil
local v_u_34 = nil
local v_u_35 = nil
local v_u_36 = nil
local v_u_37 = nil
local v_u_38 = nil
local v_u_39 = nil
local v_u_40 = nil
local v_u_41 = nil
local v_u_42 = nil
local v_u_43 = nil
local v_u_44 = nil
local v_u_45 = nil
v30:require_client(function() --[[ Line: 68 ]]
    --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_32, (ref 3): v_u_33, (ref 4): v_u_34, (ref 5): v_u_35, (ref 6): v_u_36, (ref 7): v_u_37, (ref 8): v_u_38, (ref 9): v_u_39, (ref 10): v_u_40, (ref 11): v_u_41, (ref 12): v_u_42, (ref 13): v_u_43, (ref 14): v_u_44, (ref 15): v_u_45 ]]
    v_u_31 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
    v_u_32 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_33 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.GenericArtistEventInfo)
    v_u_34 = require(game.ReplicatedStorage.Lobby.Menus.Event.GenericArtistEventUI)
    v_u_35 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.GenericArtistP2EventInfo)
    v_u_36 = require(game.ReplicatedStorage.Lobby.Menus.Event.GenericArtistP2EventUI)
    v_u_37 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.GenericArtistP3EventInfo)
    v_u_38 = require(game.ReplicatedStorage.Lobby.Menus.Event.GenericArtistP3EventUI)
    v_u_39 = require(game.ReplicatedStorage.Lobby.Menus.CraftingMaterialsAcquiredUI)
    v_u_40 = require(game.ReplicatedStorage.Lobby.NPC.NPC_JumpChallengeDemo)
    v_u_41 = require(game.ReplicatedStorage.Lobby.NPC.NPC_SummerJumpPuzzle)
    v_u_42 = require(game.ReplicatedStorage.Lobby.NPC.NPC_CarnivalJumpPuzzle)
    v_u_43 = require(game.ReplicatedStorage.Lobby.NPC.NPC_AutumnJumpPuzzle)
    v_u_44 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.MiscEventInfo)
    v_u_45 = require(game.ReplicatedStorage.Lobby.Menus.Event.ListeningPartyPreviewUI)
end)
return {
    ["new"] = function(_, p_u_46, p_u_47) --[[ Name: new ]] --[[ Line: 93 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_7, (copy 4): v_u_8, (copy 5): v_u_5, (copy 6): v_u_29, (copy 7): v_u_11, (ref 8): v_u_32, (copy 9): s_MarketplaceService_0, (copy 10): v_u_1, (ref 11): v_u_43, (copy 12): v_u_14, (copy 13): v_u_15, (copy 14): v_u_16, (copy 15): v_u_17, (copy 16): v_u_18, (copy 17): v_u_19, (copy 18): v_u_20, (copy 19): v_u_21, (copy 20): v_u_22, (copy 21): v_u_23, (copy 22): v_u_24, (copy 23): v_u_25, (copy 24): v_u_26, (copy 25): v_u_27, (copy 26): v_u_28, (copy 27): v_u_9, (copy 28): v_u_10, (copy 29): v_u_12, (copy 30): v_u_4, (copy 31): v_u_13, (copy 32): v_u_6 ]]
        local v_u_48 = {}
        local v_u_49 = v_u_3:new()
        local v_u_50 = v_u_2:new()
        local v_u_51 = false
        local v_u_52 = nil
        local v_u_53 = nil
        local function _() --[[ Name: cons ]] --[[ Line: 101 ]]
            --[[ Upvalues: (ref 1): v_u_52, (ref 2): v_u_7, (copy 3): p_u_46, (copy 4): p_u_47, (copy 5): v_u_48, (ref 6): v_u_53, (ref 7): v_u_8 ]]
            v_u_52 = v_u_7:new(p_u_46, p_u_47, v_u_48)
            v_u_53 = v_u_8:new(p_u_46, p_u_47, v_u_48)
        end;
        v_u_48.get_web_npc_manager = function(_) --[[ Name: get_web_npc_manager ]] --[[ Line: 106 ]]
            --[[ Upvalues: (ref 1): v_u_52 ]]
            return v_u_52;
        end;
        v_u_48.get_match_preview_npc_manager = function(_) --[[ Name: get_match_preview_npc_manager ]] --[[ Line: 107 ]]
            --[[ Upvalues: (ref 1): v_u_53 ]]
            return v_u_53;
        end;
        v_u_48.initialize_npcs = function(p54) --[[ Name: initialize_npcs ]] --[[ Line: 109 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_29, (copy 3): p_u_46, (copy 4): p_u_47, (ref 5): v_u_11, (ref 6): v_u_32, (ref 7): s_MarketplaceService_0, (ref 8): v_u_1, (ref 9): v_u_43 ]]
            if v_u_5.DisableNpcs ~= true then
                p54:create_default_npcs()
                p54:create_artist_event_npc()
                p54:add_npc((v_u_29:new(p_u_46, p_u_47, "NPC_AvatarItemSale1", "Avatar Shop Accessory", "Now Available!", "rbxassetid://711635385", function() --[[ Line: 122 ]]
                    --[[ Upvalues: (ref 1): p_u_46, (ref 2): v_u_11, (ref 3): v_u_32, (ref 4): s_MarketplaceService_0, (ref 5): v_u_1 ]]
                    p_u_46._sfx_manager:play_sfx(v_u_11.SFX_MENU_OPEN)
                    p_u_46._menus:push_menu(v_u_32:new(p_u_46, p_u_46._spui, p_u_46._menus):set_text("New: Vibe Ringleader\'s Band Kit Avatar Shop Item", "Wanna represent RoBeats everywhere you go on Roblox? Try out this new Avatar Shop accessory. Vibe for life!"))
                    s_MarketplaceService_0:PromptPurchase(v_u_1:get_local_player(), 9246749817)
                end)))
                p_u_46._player_blob_manager:get_player_blob()
                v_u_43:create_npc(p_u_46, p_u_47)
                p_u_46._event_integration_manager:initialize_npcs()
            end;
        end;
        v_u_48.create_default_npcs = function(p55) --[[ Name: create_default_npcs ]] --[[ Line: 178 ]]
            --[[ Upvalues: (ref 1): v_u_14, (copy 2): p_u_46, (copy 3): p_u_47, (ref 4): v_u_15, (ref 5): v_u_16, (ref 6): v_u_17, (ref 7): v_u_18, (ref 8): v_u_19, (ref 9): v_u_20, (ref 10): v_u_1, (ref 11): v_u_21, (ref 12): v_u_22, (ref 13): v_u_23, (ref 14): v_u_24, (ref 15): v_u_25, (ref 16): v_u_26, (ref 17): v_u_27, (ref 18): v_u_28 ]]
            p55:add_npc(v_u_14:new(p_u_46, p_u_47))
            p55:add_npc(v_u_15:new(p_u_46, p_u_47))
            p55:add_npc(v_u_16:new(p_u_46, p_u_47))
            p55:add_npc(v_u_17:new(p_u_46, p_u_47))
            p55:add_npc(v_u_18:new(p_u_46, p_u_47))
            p55:add_npc(v_u_19:new(p_u_46, p_u_47))
            p55:add_npc(v_u_20:new(p_u_46, p_u_47))
            if not v_u_1:do_disable_chat() then
                p55:add_npc(v_u_21:new(p_u_46, p_u_47))
            end;
            p55:add_npc(v_u_22:new(p_u_46, p_u_47))
            p55:add_npc(v_u_23:new(p_u_46, p_u_47))
            p55:add_npc(v_u_24:new(p_u_46, p_u_47))
            p55:add_npc(v_u_25:new(p_u_46, p_u_47))
            p55:add_npc(v_u_26:new(p_u_46, p_u_47))
            p55:add_npc(v_u_27:new(p_u_46, p_u_47))
            p55:add_npc(v_u_28:new(p_u_46, p_u_47))
        end;
        v_u_48.create_artist_event_npc = function(p_u_56) --[[ Name: create_artist_event_npc ]] --[[ Line: 200 ]]
            --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_46, (ref 3): v_u_29, (copy 4): p_u_47, (ref 5): v_u_11, (ref 6): v_u_10, (ref 7): v_u_12, (ref 8): v_u_4 ]]
            local v57, v_u_58 = v_u_9:is_event_active(p_u_46._player_blob_manager:get_day_event_list())
            if v57 and v_u_9:get_event_info(v_u_58):has_lobby_npc() then
                local v75, v76 = pcall(function() --[[ Line: 203 ]]
                    --[[ Upvalues: (ref 1): v_u_9, (copy 2): v_u_58, (ref 3): v_u_29, (ref 4): p_u_46, (ref 5): p_u_47, (ref 6): v_u_11, (ref 7): v_u_10, (copy 8): p_u_56, (ref 9): v_u_12 ]]
                    local v59, v60, v61 = v_u_9:get_event_info(v_u_58):get_lobby_npc_info()
                    local v62 = typeof(v59) ~= "table" and { v59 } or v59
                    local v63 = typeof(v60) ~= "table" and { v60 } or v60
                    local v64 = typeof(v61) ~= "table" and { v61 } or v61
                    local v65 = v_u_9:get_event_shop_random_dance_assetid(v_u_58)
                    for v66 = 1, #v62 do
                        local v_u_67 = v_u_29:new(p_u_46, p_u_47, v62[v66], v63[v66], v64[v66], v65, function() --[[ Line: 229 ]]
                            --[[ Upvalues: (ref 1): p_u_46, (ref 2): v_u_11, (ref 3): p_u_47, (ref 4): v_u_10 ]]
                            p_u_46._sfx_manager:play_sfx(v_u_11.SFX_MENU_OPEN)
                            p_u_47._menus:push_menu(v_u_10:new(p_u_46, p_u_47._spui, p_u_47._menus))
                        end)
                        p_u_56:add_npc(v_u_67)
                        v_u_67:add_on_loaded_fn(function() --[[ Line: 236 ]]
                            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_58, (ref 3): v_u_67, (ref 4): v_u_12 ]]
                            local v68 = v_u_9:get_event_shop_titleids_list(v_u_58)
                            if v68:count() > 0 and v_u_67:get_nametag() then
                                local v69, v70 = v_u_67:get_nametag():get_display()
                                local v71 = v_u_12:singleton():get_title_color_for_id((v68:pop_front()))
                                v69.TextColor3 = v71
                                v70.TextColor3 = v71
                            end;
                            local v72 = v_u_9:get_event_info(v_u_58):get_lobby_npc_nametag_offset()
                            if v72 ~= nil then
                                v_u_67:set_nametag_position_offset(v72)
                            end;
                            local v73 = v_u_9:get_event_info(v_u_58):get_lobby_npc_dialogue_trigger_popup_offset()
                            local v74 = v73 ~= nil and v_u_67:get_dialogue_trigger_popup()
                            if v74 then
                                v74:set_position_offset(v73)
                            end;
                        end)
                    end;
                end)
                if v75 ~= true then
                    v_u_4:warnf("LobbyNPCManager:initialize_npcs artistevent npc error(%s)", v76)
                end;
            end;
        end;
        local v_u_77 = 1
        v_u_48.add_npc = function(_, p78) --[[ Name: add_npc ]] --[[ Line: 269 ]]
            --[[ Upvalues: (ref 1): v_u_77, (copy 2): v_u_49, (ref 3): v_u_51 ]]
            local v79 = "NPC_" .. v_u_77
            v_u_77 = v_u_77 + 1
            v_u_49:add(v79, p78)
            p78:setup()
            p78:set_assigned_npc_id(v79)
            v_u_51 = true
        end;
        v_u_48.flag_update_npcs = function(_) --[[ Name: flag_update_npcs ]] --[[ Line: 280 ]]
            --[[ Upvalues: (ref 1): v_u_51 ]]
            v_u_51 = true
        end;
        v_u_48.get_id_to_npcs = function(_) --[[ Name: get_id_to_npcs ]] --[[ Line: 284 ]]
            --[[ Upvalues: (copy 1): v_u_49 ]]
            return v_u_49;
        end;
        v_u_48.remove_npc = function(_, p80) --[[ Name: remove_npc ]] --[[ Line: 286 ]]
            --[[ Upvalues: (copy 1): v_u_50 ]]
            v_u_50:push_back(p80)
        end;
        v_u_48.try_get_npc = function(_, p81, p_u_82) --[[ Name: try_get_npc ]] --[[ Line: 290 ]]
            --[[ Upvalues: (copy 1): v_u_49, (ref 2): v_u_1 ]]
            for _, v_u_83 in v_u_49:key_itr() do
                if v_u_83:get_id() == p81 then
                    v_u_1:ptry(function() --[[ Line: 293 ]]
                        --[[ Upvalues: (copy 1): p_u_82, (copy 2): v_u_83 ]]
                        p_u_82(v_u_83)
                    end)
                    return;
                end;
            end;
        end;
        local v_u_84 = 0
        local v_u_85 = CFrame.new()
        local v_u_86 = Vector3.new()
        Vector3.new()
        local v_u_87 = v_u_2:new()
        local l_LobbyNPCManager_0 = v_u_13.Test.LobbyNPCManager
        v_u_48.update = function(_, p88) --[[ Name: update ]] --[[ Line: 307 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_50, (copy 3): v_u_49, (ref 4): v_u_4, (ref 5): v_u_51, (ref 6): v_u_53, (ref 7): v_u_13, (copy 8): l_LobbyNPCManager_0, (copy 9): p_u_47, (ref 10): v_u_52, (ref 11): v_u_1, (ref 12): v_u_85, (ref 13): v_u_84, (copy 14): v_u_87, (ref 15): v_u_86 ]]
            if v_u_5.DisableNpcs == true then
                return;
            else
                for v89 = 1, v_u_50:count() do
                    local v90 = v_u_50:get(v89)
                    local v91 = v90:get_assigned_npc_id()
                    if v_u_49:contains(v91) then
                        v_u_49:remove(v91)
                    else
                        v_u_4:warnf("LobbyNPCManager:update _npcs_to_remove did not find assigned_id(%s)", v91)
                    end;
                    v90:cleanup()
                    v_u_51 = true
                end;
                v_u_50:clear()
                v_u_53:update(p88)
                local v92 = v_u_13:singleton()
                if v92:should_run(l_LobbyNPCManager_0) ~= false then
                    local v93 = v92:get_test_state(l_LobbyNPCManager_0)
                    local v94 = v93:get_dt_scale()
                    p_u_47._input:set_frame_index_state(v93)
                    v_u_52:update(v94)
                    v_u_1:profilebegin("LobbyNPCManager:npcs_sort")
                    if v_u_1:cframe_delta(v_u_1:get_camera_cframe(), v_u_85) > 0.01 and v_u_84 > 20 or v_u_51 then
                        v_u_84 = 0
                        v_u_85 = v_u_1:get_camera_cframe()
                        v_u_87:clear()
                        for _, v95 in v_u_49:key_itr() do
                            v_u_87:push_back(v95)
                        end;
                        v_u_86 = v_u_85.p
                        v_u_87:sort(function(p96, p97) --[[ Line: 348 ]]
                            --[[ Upvalues: (ref 1): v_u_86 ]]
                            return (p97:get_position() - v_u_86).Magnitude - (p96:get_position() - v_u_86).Magnitude;
                        end)
                        v_u_51 = false
                    end;
                    v_u_84 = v_u_84 + v94
                    v_u_1:profileend()
                    v_u_1:profilebegin("LobbyNPCManager:npcs_update")
                    for v98 = 1, v_u_87:count() do
                        v_u_87:get(v98):update(v94)
                    end;
                    v_u_1:profileend()
                    p_u_47._input:set_frame_index_state(nil)
                end;
            end;
        end;
        v_u_48.cleanup = function(_) --[[ Name: cleanup ]] --[[ Line: 367 ]]
            --[[ Upvalues: (ref 1): v_u_52, (ref 2): v_u_53, (copy 3): v_u_49, (ref 4): v_u_1, (ref 5): v_u_2, (ref 6): v_u_6, (ref 7): v_u_4 ]]
            v_u_52:cleanup()
            v_u_53:cleanup()
            for _, v99 in v_u_49:key_itr() do
                v99:cleanup()
            end;
            v_u_49:clear()
            v_u_1:ptry(function() --[[ Line: 375 ]]
                --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_6, (ref 3): v_u_4 ]]
                local v100 = v_u_2:new(v_u_6:get_npc_root():GetChildren())
                if v100:count() > 0 then
                    for _, v101 in v100:key_itr() do
                        v_u_4:warnf("LobbyNPCManager:cleanup remaining model(%s)", v101.Name)
                        v101:Destroy()
                    end;
                end;
            end)
        end;
        v_u_52 = v_u_7:new(p_u_46, p_u_47, v_u_48)
        v_u_53 = v_u_8:new(p_u_46, p_u_47, v_u_48)
        return v_u_48;
    end
};
