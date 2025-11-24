-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:37 PM
-- Cached decompilation

require(game.ReplicatedStorage.Local.AnimationManager)
local v_u_1 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_2 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_3 = require(game.ReplicatedStorage.Lobby.NPC.NPCAsyncLoad)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.Lobby.Menus.DanceShopUI)
return {
    ["new"] = function(_, p6, p7) --[[ Name: new ]] --[[ Line: 12 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_3, (copy 3): v_u_2, (copy 4): v_u_5, (copy 5): v_u_1 ]]
        local function f_define_local_fns(p_u_8) --[[ Name: define_local_fns ]] --[[ Line: 13 ]]
            --[[ Upvalues: (ref 1): v_u_4 ]]
            local v_u_9 = nil
            local v_u_10 = nil
            local v_u_11 = nil
            local v_u_12 = nil
            v_u_4:ptry(function() --[[ Line: 17 ]]
                --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_8, (ref 3): v_u_11, (ref 4): v_u_12, (ref 5): v_u_10 ]]
                v_u_9 = p_u_8:get_root().ScreenDisplay.SurfaceGui
                v_u_9.Enabled = false
                v_u_11 = v_u_9.Frame.Icon
                v_u_12 = v_u_9.Frame.DanceNameDisplay
                v_u_10 = p_u_8:get_root().Light.PointLight
                v_u_10.Enabled = false
            end)
            p_u_8.set_screen_visible = function(_, p_u_13) --[[ Name: set_screen_visible ]] --[[ Line: 28 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_9, (ref 3): v_u_10 ]]
                v_u_4:ptry(function() --[[ Line: 29 ]]
                    --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_13, (ref 3): v_u_10 ]]
                    v_u_9.Enabled = p_u_13
                    v_u_10.Enabled = p_u_13
                end)
            end;
            p_u_8.get_screen_display_root = function(_) --[[ Name: get_screen_display_root ]] --[[ Line: 34 ]]
                --[[ Upvalues: (ref 1): v_u_9 ]]
                return v_u_9;
            end;
            p_u_8.get_screen_icon = function(_) --[[ Name: get_screen_icon ]] --[[ Line: 37 ]]
                --[[ Upvalues: (ref 1): v_u_11 ]]
                return v_u_11;
            end;
            p_u_8.get_screen_name_display = function(_) --[[ Name: get_screen_name_display ]] --[[ Line: 40 ]]
                --[[ Upvalues: (ref 1): v_u_12 ]]
                return v_u_12;
            end;
            p_u_8.set_title_visible = function(p14, p15) --[[ Name: set_title_visible ]] --[[ Line: 44 ]]
                p14:get_nametag():set_override_gui_enabled(p15)
            end;
        end;
        return v_u_3:new(p6, p7, v_u_2.NPC.NPC_DanceMachine, "Dance R-volution Machine", "Dance Shop", game.ReplicatedStorage.LobbyElementProtos.CharacterOverlay.DialoguePopupDanceShop, true, function(p16, _, _) --[[ Line: 57 ]]
            --[[ Upvalues: (copy 1): f_define_local_fns ]]
            f_define_local_fns(p16)
        end, function(p17, p18, p19) --[[ Line: 60 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_1 ]]
            p19:push_menu(v_u_5:new(p17, p18, p19))
            p17._sfx_manager:play_sfx(v_u_1.SFX_MENU_OPEN)
        end);
    end
};
