-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:56 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_2 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_3 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.Lobby.Menus.SettingsUI)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.LocalShared.LocalSharedSettingsUIUtil)
return {
    ["new"] = function(_, p_u_7, p_u_8, p_u_9, p_u_10, p_u_11) --[[ Name: new ]] --[[ Line: 14 ]]
        --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_2, (copy 3): v_u_4, (copy 4): v_u_1, (copy 5): v_u_3, (copy 6): v_u_5 ]]
        local v12 = {}
        local v_u_13 = nil
        local v_u_14 = nil
        local v_u_15 = nil
        local v_u_16 = nil
        local function f_cons() --[[ Name: cons ]] --[[ Line: 19 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_6, (copy 3): p_u_7, (copy 4): p_u_8, (copy 5): p_u_9, (copy 6): p_u_10, (ref 7): v_u_2, (ref 8): v_u_4, (ref 9): v_u_14, (ref 10): v_u_15, (ref 11): v_u_16, (ref 12): v_u_1, (ref 13): v_u_3, (ref 14): v_u_5 ]]
            v_u_13 = v_u_6:create_keybinds_button(p_u_7, p_u_8, p_u_9, p_u_10.KeybindsButton)
            local v17 = v_u_2:button_bind_anim_toggle(v_u_13, function() --[[ Line: 21 ]]
                --[[ Upvalues: (ref 1): p_u_8 ]]
                return p_u_8:get_alpha();
            end)
            if v_u_4:is_mobile() then
                v17:set_toggle(false)
            end;
            v_u_14 = v_u_6:create_note_speed_button(p_u_7, p_u_8, p_u_9, p_u_10.NoteSpeedButton)
            v_u_15 = v_u_6:create_note_display_settings_button(p_u_7, p_u_9, p_u_8, p_u_10.NoteDisplayModeButton)
            v_u_16 = p_u_8:add_cycle_element(p_u_7, 1, v_u_2:new(v_u_1:new(p_u_8, p_u_9.PrimaryPart, p_u_10.SettingsButton), p_u_7._spui, function() --[[ Line: 31 ]]
                --[[ Upvalues: (ref 1): p_u_7, (ref 2): v_u_3, (ref 3): v_u_5 ]]
                p_u_7._sfx_manager:play_sfx(v_u_3.SFX_MENU_OPEN)
                p_u_7._menus:push_menu(v_u_5:new(p_u_7, p_u_7._spui, p_u_7._menus))
            end))
        end;
        v12.set_visible = function(_, p18) --[[ Name: set_visible ]] --[[ Line: 38 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_14, (ref 3): v_u_15, (ref 4): v_u_16, (copy 5): p_u_11 ]]
            v_u_13:set_visible(p18)
            v_u_14:set_visible(p18)
            v_u_15:set_visible(p18)
            v_u_16:set_visible(p18)
            p_u_11.Visible = p18
        end;
        f_cons()
        return v12;
    end
};
