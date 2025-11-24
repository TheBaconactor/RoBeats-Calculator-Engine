-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:59 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_5 = require(game.ReplicatedStorage.Menu.CharacterDialogue)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
local v7 = {}
local v_u_8 = false
local v_u_9 = v2:new():push_back_table_list({
    {
        ["Zara"] = "Getting the right look is one of the most important parts of being a star. You\'re in the right place!",
        ["Firsttime"] = true
    },
    {
        ["Zara"] = "As they say, clothes make the man. So, what ARE we going to make of you?"
    },
    {
        ["Zara"] = "I\'ve got the latest fashions straight from the runway... just for you!"
    }
})
local v_u_10 = v2:new():push_back_table_list({})
local v_u_11 = v2:new():push_back_table_list({
    {
        ["Zara"] = "You\'ve GOT to dress in style if you want to be at your best."
    },
    {
        ["Zara"] = "Oh my, just look at those... rags! We\'ll get that fixed up in no time."
    },
    {
        ["Zara"] = "A marvelous outfit will make any star just... shine!"
    }
})
local v_u_12 = v2:new():push_back_table_list({
    {
        ["Zara"] = "That\'s going to look absolutely amazing on you."
    }
})
v7.new = function(_, p_u_13, p_u_14, p_u_15, p_u_16) --[[ Name: new ]] --[[ Line: 41 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_3, (copy 3): v_u_4, (copy 4): v_u_6, (copy 5): v_u_1, (copy 6): v_u_10, (copy 7): v_u_12, (copy 8): v_u_9, (ref 9): v_u_8, (copy 10): v_u_11 ]]
    local v17 = {}
    local v_u_18 = nil
    local v_u_19 = nil
    v17.cons = function(p_u_20) --[[ Name: cons ]] --[[ Line: 47 ]]
        --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_5, (copy 3): p_u_16, (ref 4): v_u_3, (copy 5): p_u_15, (ref 6): v_u_19, (copy 7): p_u_14, (copy 8): p_u_13, (ref 9): v_u_4, (ref 10): v_u_6 ]]
        v_u_18 = v_u_5:new("Zara", p_u_16.ZaraDialogue, v_u_3:new(p_u_15, p_u_16.PrimaryPart, p_u_16.ZaraDialogue))
        v_u_19 = p_u_14:add_cycle_element(p_u_13, 1, v_u_4:new(v_u_3:new(p_u_14, p_u_16.PrimaryPart, p_u_16.Zara), p_u_13._spui, function() --[[ Line: 57 ]]
            --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_6, (copy 3): p_u_20 ]]
            p_u_13._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            p_u_20:load_from_pressed_dialogues("Zara")
        end):set_selected_tar_scale(1.05):set_triggered_scale_offset(0.1))
        p_u_20:load_from_startup_dialogues()
    end;
    local v_u_21 = false
    v17.set_locked = function(_, p22) --[[ Name: set_locked ]] --[[ Line: 67 ]]
        --[[ Upvalues: (ref 1): v_u_21 ]]
        v_u_21 = p22
    end;
    v17.item_selected = function(p23, p_u_24) --[[ Name: item_selected ]] --[[ Line: 71 ]]
        --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_1, (ref 3): v_u_10 ]]
        if v_u_21 ~= true then
            local v26 = v_u_1:splist_filter(v_u_10, function(p25) --[[ Line: 73 ]]
                --[[ Upvalues: (copy 1): p_u_24 ]]
                return p_u_24 == p25.GearID;
            end)
            if v26:count() > 0 then
                p23:load_dialogue(v26:random())
            end;
        end;
    end;
    v17.item_purchased = function(p27) --[[ Name: item_purchased ]] --[[ Line: 81 ]]
        --[[ Upvalues: (ref 1): v_u_12 ]]
        p27:load_dialogue(v_u_12:random())
    end;
    v17.load_from_startup_dialogues = function(p28) --[[ Name: load_from_startup_dialogues ]] --[[ Line: 85 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_9, (ref 3): v_u_8 ]]
        local v30 = v_u_1:splist_filter(v_u_9, function(p29) --[[ Line: 86 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            if v_u_8 == false then
                return p29.Firsttime == true;
            else
                return p29.Firsttime ~= true;
            end;
        end)
        v_u_8 = true
        p28:load_dialogue(v30:random())
    end;
    v17.load_from_pressed_dialogues = function(p31, p_u_32) --[[ Name: load_from_pressed_dialogues ]] --[[ Line: 97 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_11 ]]
        p31:load_dialogue(v_u_1:splist_filter(v_u_11, function(p33) --[[ Line: 98 ]]
            --[[ Upvalues: (copy 1): p_u_32 ]]
            return p33[p_u_32] ~= nil;
        end):random())
    end;
    v17.load_dialogue = function(_, p34) --[[ Name: load_dialogue ]] --[[ Line: 104 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        local v35
        if p34 == nil then
            v35 = nil
        else
            v35 = p34.Zara
        end;
        if v35 == nil then
            v_u_18:finish()
        else
            v_u_18:display_text(v35)
        end;
    end;
    local function _(p36) --[[ Name: dialogue_time_finish ]] --[[ Line: 117 ]]
        if p36:is_displayed() and p36:get_time_displayed() > 5 then
            p36:finish()
        end;
    end;
    v17.update = function(_, p37) --[[ Name: update ]] --[[ Line: 123 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        v_u_18:update(p37)
        local v38 = v_u_18
        if v38:is_displayed() and v38:get_time_displayed() > 5 then
            v38:finish()
        end;
    end;
    v17.layout = function(_) --[[ Name: layout ]] --[[ Line: 129 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        v_u_18:layout()
    end;
    v17.set_alpha = function(_, p39) --[[ Name: set_alpha ]] --[[ Line: 133 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        v_u_18:set_alpha(p39)
    end;
    v17:cons()
    return v17;
end;
return v7;
