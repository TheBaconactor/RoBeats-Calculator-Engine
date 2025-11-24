-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:58 PM
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
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v7 = require(game.ReplicatedStorage.PlayerInfo.PurchaseInfo)
local v8 = {}
local v_u_9 = false
local v_u_10 = v2:new():push_back_table_list({
    {
        ["Mattie"] = "Everything you need, right here! C\'mon, don\'t be shy!",
        ["Firsttime"] = true
    },
    {
        ["Mattie"] = "I\'ve got something for everyone! So, what will it be?",
        ["Firsttime"] = true
    },
    {
        ["Mattie"] = "I had a feeling you\'d be back! So, what can I get you?"
    },
    {
        ["Mattie"] = "Can\'t keep away for long! So, what will it be?"
    }
})
local v_u_11 = v2:new():push_back_table_list({
    {
        ["Mattie"] = "Thinking about the starter pack? It\'s a great deal! All nine beginner songs AND some stars. A must-buy!",
        ["PurchaseID"] = v7.ProductID_StarterPack
    }
})
local v_u_12 = v2:new():push_back_table_list({
    {
        ["Mattie"] = "It\'s... pretty hard to obtain a bunch of stars outside of using Robux. It\'s a premium currency!"
    },
    {
        ["Mattie"] = "You ever heard anyone say... Money makes the world go round? Well, it\'s true!"
    },
    {
        ["Mattie"] = "Treat yourself to something nice! I\'ve got options for every budget."
    },
    {
        ["Mattie"] = "Free stars..? Not a chance!"
    },
    {
        ["Mattie"] = "You calling me pay-to-win? I prefer the term... play to win!"
    }
})
local v_u_13 = v2:new():push_back_table_list({
    {
        ["Mattie"] = "Thanks! All proceeds will be going to... well... somewhere good!"
    },
    {
        ["Mattie"] = "Every dollar saves... someone! Thanks again!"
    }
})
v8.new = function(_, p_u_14, p_u_15, p_u_16, p_u_17) --[[ Name: new ]] --[[ Line: 48 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_3, (copy 3): v_u_4, (copy 4): v_u_6, (copy 5): v_u_1, (copy 6): v_u_11, (copy 7): v_u_13, (copy 8): v_u_10, (ref 9): v_u_9, (copy 10): v_u_12 ]]
    local v18 = {}
    local v_u_19 = nil
    local v_u_20 = nil
    v18.cons = function(p_u_21) --[[ Name: cons ]] --[[ Line: 54 ]]
        --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_5, (copy 3): p_u_17, (ref 4): v_u_3, (copy 5): p_u_16, (ref 6): v_u_20, (copy 7): p_u_15, (copy 8): p_u_14, (ref 9): v_u_4, (ref 10): v_u_6 ]]
        v_u_19 = v_u_5:new("Roxie", p_u_17.RoxieDialogue, v_u_3:new(p_u_16, p_u_17.PrimaryPart, p_u_17.RoxieDialogue))
        v_u_20 = p_u_15:add_cycle_element(p_u_14, 1, v_u_4:new(v_u_3:new(p_u_15, p_u_17.PrimaryPart, p_u_17.Roxie), p_u_14._spui, function() --[[ Line: 64 ]]
            --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_6, (copy 3): p_u_21 ]]
            p_u_14._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            p_u_21:load_from_pressed_dialogues("Mattie")
        end):set_selected_tar_scale(1.05):set_triggered_scale_offset(0.1))
        p_u_21:load_from_startup_dialogues()
    end;
    v18.item_selected = function(p22, p_u_23) --[[ Name: item_selected ]] --[[ Line: 73 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_11 ]]
        local v25 = v_u_1:splist_filter(v_u_11, function(p24) --[[ Line: 74 ]]
            --[[ Upvalues: (copy 1): p_u_23 ]]
            return p_u_23 == p24.PurchaseID;
        end)
        if v25:count() > 0 then
            p22:load_dialogue(v25:random())
        end;
    end;
    v18.item_purchased = function(p26) --[[ Name: item_purchased ]] --[[ Line: 82 ]]
        --[[ Upvalues: (ref 1): v_u_13 ]]
        p26:load_dialogue(v_u_13:random())
    end;
    v18.load_from_startup_dialogues = function(p27) --[[ Name: load_from_startup_dialogues ]] --[[ Line: 86 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_10, (ref 3): v_u_9 ]]
        local v29 = v_u_1:splist_filter(v_u_10, function(p28) --[[ Line: 87 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            if v_u_9 == false then
                return p28.Firsttime == true;
            else
                return p28.Firsttime ~= true;
            end;
        end)
        v_u_9 = true
        p27:load_dialogue(v29:random())
    end;
    v18.load_from_pressed_dialogues = function(p30, p_u_31) --[[ Name: load_from_pressed_dialogues ]] --[[ Line: 98 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_12 ]]
        p30:load_dialogue(v_u_1:splist_filter(v_u_12, function(p32) --[[ Line: 99 ]]
            --[[ Upvalues: (copy 1): p_u_31 ]]
            return p32[p_u_31] ~= nil;
        end):random())
    end;
    v18.load_dialogue = function(_, p33) --[[ Name: load_dialogue ]] --[[ Line: 105 ]]
        --[[ Upvalues: (copy 1): p_u_14, (ref 2): v_u_19 ]]
        if p33 == nil then
            return;
        else
            local l_Mattie_0 = p33.Mattie
            if l_Mattie_0 == nil then
                v_u_19:finish()
            else
                p_u_14._update_enqueue_fn:enqueue_function(function() --[[ Line: 110 ]]
                    --[[ Upvalues: (ref 1): v_u_19, (copy 2): l_Mattie_0 ]]
                    v_u_19:display_text(l_Mattie_0)
                end, 0)
            end;
        end;
    end;
    local function _(p34) --[[ Name: dialogue_time_finish ]] --[[ Line: 118 ]]
        if p34:is_displayed() and p34:get_time_displayed() > 5 then
            p34:finish()
        end;
    end;
    v18.update = function(_, p35) --[[ Name: update ]] --[[ Line: 124 ]]
        --[[ Upvalues: (ref 1): v_u_19 ]]
        v_u_19:update(p35)
        local v36 = v_u_19
        if v36:is_displayed() and v36:get_time_displayed() > 5 then
            v36:finish()
        end;
    end;
    v18.layout = function(_) --[[ Name: layout ]] --[[ Line: 130 ]]
        --[[ Upvalues: (ref 1): v_u_19 ]]
        v_u_19:layout()
    end;
    v18.set_alpha = function(_, p37) --[[ Name: set_alpha ]] --[[ Line: 134 ]]
        --[[ Upvalues: (ref 1): v_u_19 ]]
        v_u_19:set_alpha(p37)
    end;
    v18:cons()
    return v18;
end;
return v8;
