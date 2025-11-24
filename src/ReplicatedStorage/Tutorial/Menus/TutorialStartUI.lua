-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:15 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_2 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_4 = require(game.ReplicatedStorage.Menu.SPUIDisplay)
require(game.ReplicatedStorage.Shared.SPVector)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_8 = require(game.ReplicatedStorage.Menu.CharacterDialogue)
local v_u_9 = require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_10 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_11 = require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_12 = require(game.ReplicatedStorage.Tutorial.TutorialData)
local v_u_13 = require(game.ReplicatedStorage.LocalShared.BGMManager)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_14 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_15 = {
    ["Mode"] = {
        ["InitialDialogue"] = 1,
        ["StarletIn"] = 2,
        ["StarletDialogue"] = 3,
        ["ChoiceWindowIn"] = 4,
        ["ChoiceDisplayed"] = 5,
        ["SkipInitialDialogue"] = 6
    }
}
v_u_15.new = function(_, p_u_16, p_u_17, p_u_18) --[[ Name: new ]] --[[ Line: 35 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_15, (copy 3): v_u_14, (copy 4): v_u_12, (copy 5): v_u_13, (copy 6): v_u_7, (copy 7): v_u_4, (copy 8): v_u_8, (copy 9): v_u_3, (copy 10): v_u_1, (copy 11): v_u_10, (copy 12): v_u_6, (copy 13): v_u_11, (copy 14): v_u_9, (copy 15): v_u_5 ]]
    local v19 = v_u_2:new(p_u_17, p_u_18)
    local v_u_20 = nil
    local v_u_21 = nil
    local v_u_22 = nil
    local v_u_23 = nil
    local v_u_24 = nil
    local v_u_25 = nil
    local v_u_26 = 1
    local v_u_27 = nil
    local v_u_28 = nil
    local v_u_29 = nil
    local v_u_30 = nil
    local v_u_31 = nil
    local v_u_32 = nil
    local v_u_33 = nil
    local v_u_34 = nil
    local v_u_35 = 1
    local l_InitialDialogue_0 = v_u_15.Mode.InitialDialogue
    if v_u_14.TutorialSkipInitialDialogue == true then
        l_InitialDialogue_0 = v_u_15.Mode.SkipInitialDialogue
    end;
    local v_u_36 = 0
    local v_u_37 = true
    v19.cons = function(p_u_38) --[[ Name: cons ]] --[[ Line: 67 ]]
        --[[ Upvalues: (ref 1): v_u_12, (copy 2): p_u_16, (ref 3): v_u_13, (ref 4): v_u_20, (ref 5): v_u_7, (ref 6): v_u_24, (ref 7): v_u_4, (copy 8): p_u_17, (ref 9): v_u_23, (ref 10): v_u_8, (ref 11): v_u_14, (ref 12): v_u_21, (ref 13): v_u_22, (ref 14): v_u_3, (ref 15): v_u_25, (ref 16): v_u_1, (ref 17): v_u_27, (ref 18): v_u_28, (ref 19): v_u_31, (ref 20): v_u_10, (ref 21): v_u_6, (ref 22): v_u_32, (ref 23): v_u_33, (ref 24): v_u_34, (ref 25): v_u_29, (ref 26): v_u_30 ]]
        v_u_12:set_camera_start()
        p_u_16._bgm_manager:play_bgm(v_u_13.BGM_LOBBY)
        v_u_20 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.TutorialStartUI:Clone()
        v_u_20.Parent = v_u_7:get_world_ui_folder()
        p_u_38._native_size = v_u_20.PrimaryPart.Size
        p_u_38._size = p_u_38._native_size
        v_u_24 = v_u_4:new(v_u_20.NarratorDialogue, p_u_17):set_position_nxy(0.5, 0.5):set_anchor_rnxy(0.5, 0.5)
        v_u_23 = v_u_8:new(nil, v_u_20.NarratorDialogue.PrimaryPart, v_u_24)
        if v_u_14.TutorialSkipInitialDialogue ~= true then
            v_u_23:display_text("You\'ve always dreamed of becoming a star. And now... you\'re finally here.\nThe big city. It\'s the place to be!")
        end;
        v_u_21 = v_u_4:new(v_u_20.Starlet, p_u_17, true):set_position_nxy(0.05, 0.95):set_anchor_rnxy(0, 1)
        v_u_22 = v_u_8:new("Starlet", v_u_20.Starlet.Dialogue, v_u_3:new(v_u_21, v_u_20.Starlet.PrimaryPart, v_u_20.Starlet.Dialogue))
        v_u_25 = v_u_1:get_list_of_children_of_classname(v_u_20.Starlet.PrimaryPart, "ImageLabel")
        p_u_38:scarlet_anim_in(0)
        v_u_27 = v_u_20.ChoiceWindow
        local l_Window_0 = v_u_27.Window
        v_u_28 = v_u_4:new(l_Window_0, p_u_17, true)
        v_u_31 = p_u_38:add_cycle_element(p_u_16, 1, v_u_10:new(v_u_3:new(v_u_28, l_Window_0.PrimaryPart, v_u_27.StartButton), p_u_17, function() --[[ Line: 108 ]]
            --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_6, (copy 3): p_u_38 ]]
            p_u_16._sfx_manager:play_sfx(v_u_6.SFX_MENU_OPEN)
            p_u_38:choice_select(true)
        end):set_passive_anim(true))
        v_u_32 = p_u_38:add_cycle_element(p_u_16, 1, v_u_10:new(v_u_3:new(v_u_28, l_Window_0.PrimaryPart, v_u_27.SkipButton), p_u_17, function() --[[ Line: 116 ]]
            --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_6, (copy 3): p_u_38 ]]
            p_u_16._sfx_manager:play_sfx(v_u_6.SFX_MENU_CLOSE)
            p_u_38:choice_select(false)
        end))
        v_u_28:set_position_nxy(0.5, 0.5):set_anchor_rnxy(0.5, 0.5)
        v_u_31:set_enabled(false)
        v_u_32:set_enabled(false)
        v_u_33 = v_u_1:get_list_of_children_of_classname(v_u_27.SkipButton, "ImageLabel")
        v_u_34 = v_u_1:get_list_of_children_of_classname(v_u_27.SkipButton, "TextLabel")
        v_u_29 = v_u_1:get_list_of_children_of_classname(v_u_27, "ImageLabel")
        v_u_30 = v_u_1:get_list_of_children_of_classname(v_u_27, "TextLabel")
        v_u_29:remove_if(function(p39, _) --[[ Line: 131 ]]
            --[[ Upvalues: (ref 1): v_u_33 ]]
            return v_u_33:contains(p39);
        end)
        v_u_30:remove_if(function(p40, _) --[[ Line: 132 ]]
            --[[ Upvalues: (ref 1): v_u_34 ]]
            return v_u_34:contains(p40);
        end)
        p_u_38:choice_window_anim_in(0)
        p_u_38:layout()
    end;
    v19.layout = function(_) --[[ Name: layout ]] --[[ Line: 139 ]]
        --[[ Upvalues: (copy 1): p_u_17, (ref 2): v_u_24, (ref 3): v_u_21, (ref 4): v_u_26, (ref 5): v_u_28, (ref 6): v_u_35, (ref 7): v_u_23, (ref 8): v_u_22 ]]
        p_u_17:uiobj_rescale_to_max_nxy(v_u_24, 0.9, 0.75, 1)
        p_u_17:uiobj_rescale_to_max_nxy(v_u_21, 0.25, 0.5, v_u_26)
        p_u_17:uiobj_rescale_to_max_nxy(v_u_28, 0.5, 0.5, v_u_35)
        v_u_28:layout()
        v_u_21:layout()
        v_u_23:layout()
        v_u_22:layout()
    end;
    v19.behaviour_update = function(p41, p42, _) --[[ Name: behaviour_update ]] --[[ Line: 149 ]]
        --[[ Upvalues: (copy 1): p_u_16, (ref 2): v_u_11, (ref 3): v_u_9, (ref 4): l_InitialDialogue_0, (ref 5): v_u_15, (ref 6): v_u_6, (ref 7): v_u_23, (ref 8): v_u_36, (ref 9): v_u_5, (ref 10): v_u_22, (ref 11): v_u_31, (ref 12): v_u_32 ]]
        p41:behaviour_update_base(p42, p_u_16)
        if p41._current_mode == v_u_11.MODE_OPEN then
            local v43 = p_u_16._input:control_just_pressed(v_u_9.KEY_CLICK)
            if l_InitialDialogue_0 == v_u_15.Mode.InitialDialogue then
                local v44 = false
                if v43 == true then
                    p_u_16._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                    if v_u_23:is_displayed() == false then
                        v_u_23:force_display()
                    else
                        v_u_23:finish()
                        v44 = true
                    end;
                end;
                if v44 == true then
                    l_InitialDialogue_0 = v_u_15.Mode.StarletIn
                    v_u_36 = 0
                end;
            elseif l_InitialDialogue_0 == v_u_15.Mode.StarletIn then
                local v45, v46 = v_u_5:incr_clamp(v_u_36, v_u_5:SecondsToTick(0.25) * p42, 0, 1)
                v_u_36 = v45
                p41:scarlet_anim_in(v_u_36)
                if v46 == true then
                    l_InitialDialogue_0 = v_u_15.Mode.StarletDialogue
                    v_u_22:display_text("Hey there! My name\'s Starlet.\nWe get a lot of newcomers, so I\'m here to help. Wanna learn how to play?")
                end;
            elseif l_InitialDialogue_0 == v_u_15.Mode.StarletDialogue then
                local v47 = false
                if v43 == true then
                    p_u_16._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                    if v_u_22:is_displayed() == false then
                        v_u_22:force_display()
                    else
                        v_u_22:finish()
                        v47 = true
                    end;
                end;
                if v47 == true then
                    l_InitialDialogue_0 = v_u_15.Mode.ChoiceWindowIn
                    v_u_36 = 0
                end;
            elseif l_InitialDialogue_0 == v_u_15.Mode.ChoiceWindowIn then
                local v48, v49 = v_u_5:incr_clamp(v_u_36, v_u_5:SecondsToTick(0.25) * p42, 0, 1)
                v_u_36 = v48
                p41:choice_window_anim_in(v_u_36)
                if v49 == true then
                    v_u_31:set_enabled(true)
                    v_u_32:set_enabled(true)
                    l_InitialDialogue_0 = v_u_15.Mode.ChoiceDisplayed
                end;
            elseif l_InitialDialogue_0 == v_u_15.Mode.SkipInitialDialogue then
                local v50, v51 = v_u_5:incr_clamp(v_u_36, v_u_5:SecondsToTick(0.25) * p42, 0, 1)
                v_u_36 = v50
                p41:scarlet_anim_in(v_u_36)
                p41:choice_window_anim_in(v_u_36)
                if v51 == true then
                    v_u_22:display_text("Hey there! My name\'s Starlet.\nWe get a lot of newcomers, so I\'m here to help. Wanna learn how to play?")
                    v_u_31:set_enabled(true)
                    v_u_32:set_enabled(true)
                    l_InitialDialogue_0 = v_u_15.Mode.ChoiceDisplayed
                end;
            end;
            v_u_23:update(p42)
            v_u_22:update(p42)
        end;
    end;
    v19.scarlet_anim_in = function(_, p52) --[[ Name: scarlet_anim_in ]] --[[ Line: 226 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_25, (ref 3): v_u_20, (ref 4): v_u_26, (ref 5): v_u_5 ]]
        v_u_1:list_set_alpha_name(v_u_25, {
            ["ImageAlpha"] = p52
        })
        v_u_1:r_set_alpha(v_u_20.Starlet.PrimaryPart, 1)
        v_u_26 = v_u_5:YForPointOf2PtLineP1P2X(0, 1.25, 1, 1, p52)
    end;
    v19.choice_window_anim_in = function(_, p53) --[[ Name: choice_window_anim_in ]] --[[ Line: 232 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_29, (ref 3): v_u_30, (ref 4): v_u_33, (ref 5): v_u_34, (ref 6): v_u_27, (ref 7): v_u_35, (ref 8): v_u_5 ]]
        v_u_1:list_set_alpha_name(v_u_29, {
            ["ImageAlpha"] = p53
        })
        v_u_1:list_set_alpha_name(v_u_30, {
            ["TextAlpha"] = p53
        })
        v_u_1:list_set_alpha_name(v_u_33, {
            ["ImageAlpha"] = p53 * 0.5
        })
        v_u_1:list_set_alpha_name(v_u_34, {
            ["TextAlpha"] = p53 * 0.5
        })
        v_u_1:r_set_alpha(v_u_27, 1)
        v_u_35 = v_u_5:YForPointOf2PtLineP1P2X(0, 1.25, 1, 1, p53)
    end;
    v19.choice_select = function(p54, p55) --[[ Name: choice_select ]] --[[ Line: 241 ]]
        --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_32, (ref 3): v_u_37, (copy 4): p_u_18 ]]
        v_u_31:set_enabled(false)
        v_u_32:set_enabled(false)
        if p55 == true then
            v_u_37 = true
        else
            v_u_37 = false
        end;
        p_u_18:remove_menu(p54)
    end;
    v19.transition_update_visual = function(p56, _) --[[ Name: transition_update_visual ]] --[[ Line: 252 ]]
        --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_5, (ref 3): v_u_1, (ref 4): v_u_25, (ref 5): v_u_20, (ref 6): v_u_26, (ref 7): v_u_29, (ref 8): v_u_30, (ref 9): v_u_33, (ref 10): v_u_34, (ref 11): v_u_27, (ref 12): v_u_35 ]]
        if p56._current_mode == v_u_11.MODE_TRANSITION_OUT then
            local v57 = v_u_5:YForPointOf2PtLine(Vector2.new(0, 1), Vector2.new(1, 1.25), p56._transition_t)
            local v58 = v_u_5:YForPointOf2PtLine(Vector2.new(0, 1), Vector2.new(1, 0), p56._transition_t)
            v_u_1:list_set_alpha_name(v_u_25, {
                ["ImageAlpha"] = v58
            })
            v_u_1:r_set_alpha(v_u_20.Starlet.PrimaryPart, 1)
            v_u_26 = v_u_5:YForPointOf2PtLineP1P2X(0, 1.25, 1, 1, v57)
            v_u_1:list_set_alpha_name(v_u_29, {
                ["ImageAlpha"] = v58
            })
            v_u_1:list_set_alpha_name(v_u_30, {
                ["TextAlpha"] = v58
            })
            v_u_1:list_set_alpha_name(v_u_33, {
                ["ImageAlpha"] = v58 * 0.5
            })
            v_u_1:list_set_alpha_name(v_u_34, {
                ["TextAlpha"] = v58 * 0.5
            })
            v_u_1:r_set_alpha(v_u_27, 1)
            v_u_35 = v_u_5:YForPointOf2PtLineP1P2X(0, 1.25, 1, 1, v57)
        end;
    end;
    v19.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 270 ]]
        --[[ Upvalues: (ref 1): v_u_20, (copy 2): p_u_16, (ref 3): v_u_37 ]]
        v_u_20:Destroy()
        p_u_16._tutorial_manager:tutorial_start_do_tutorial(v_u_37)
    end;
    v19.get_native_size = function(p59) --[[ Name: get_native_size ]] --[[ Line: 276 ]]
        return p59._native_size;
    end;
    v19.get_size = function(p60) --[[ Name: get_size ]] --[[ Line: 279 ]]
        return p60._size;
    end;
    v19.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 283 ]]
        --[[ Upvalues: (ref 1): v_u_20 ]]
        return v_u_20.PrimaryPart.Position;
    end;
    v19.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 286 ]]
        --[[ Upvalues: (ref 1): v_u_20 ]]
        return v_u_20.PrimaryPart.SurfaceGui;
    end;
    v19:cons()
    return v19;
end;
return v_u_15;
